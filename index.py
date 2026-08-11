import asyncio
import logging
import os
import json
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from prediction_system import UltraPredictionSystem
from config import user_manager, ADMIN_IDS
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ──────────────────────────────────────────────
TOKEN = os.getenv('BOT_TOKEN')
API_HISTORY = 'https://web-tool-4ej3.onrender.com/api/lc79/history'
FETCH_INTERVAL = 10

# ── LOGGING ─────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── HỆ THỐNG DỰ ĐOÁN ───────────────────────────────────
prediction_system = UltraPredictionSystem()
last_session = None
last_data = None

# ── DECORATOR KIỂM TRA QUYỀN ───────────────────────────
def require_auth(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        username = update.effective_user.username or f"user_{user_id}"
        
        # Kiểm tra user
        is_valid, result = user_manager.check_user(user_id)
        
        if not is_valid:
            keyboard = [
                [InlineKeyboardButton("🔑 Đăng ký key", callback_data='register')],
                [InlineKeyboardButton("📱 Liên hệ admin", url='https://t.me/hoangquan280')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"{result}\n\n"
                f"📌 Vui lòng đăng ký để sử dụng bot!\n"
                f"ID của bạn: `{user_id}`",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        # Lưu user vào context để dùng sau
        context.user_data['user_info'] = result
        context.user_data['user_id'] = user_id
        context.user_data['username'] = username
        
        return await func(update, context, *args, **kwargs)
    return wrapper

# ── LẤY DỮ LIỆU TỪ API ──────────────────────────────────
async def fetch_history():
    global last_session, last_data
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_HISTORY, headers={'Accept': 'application/json'}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'OK':
                        items = data.get('data', [])
                        if items:
                            valid = None
                            for item in items:
                                if all(k in item for k in ['d1', 'd2', 'd3', 'phiên', 'kết_quả']):
                                    valid = item
                                    break
                            
                            if valid and valid['phiên'] != last_session:
                                last_session = valid['phiên']
                                last_data = valid
                                return valid
    except Exception as e:
        logger.error(f"❌ Lỗi fetch API: {e}")
    return None

# ── XỬ LÝ DỮ LIỆU ──────────────────────────────────────
def process_data(data):
    if not data:
        return None
    
    phien = data.get('phiên', '--')
    d1 = data.get('d1', 0)
    d2 = data.get('d2', 0)
    d3 = data.get('d3', 0)
    tong = data.get('tổng', d1 + d2 + d3)
    ket_qua_raw = data.get('kết_quả', '')
    
    if ket_qua_raw in ['tai', 'Tài', 'T', 't']:
        ket_qua = 'T'
        ket_qua_text = 'TÀI'
    elif ket_qua_raw in ['xiu', 'Xỉu', 'X', 'x']:
        ket_qua = 'X'
        ket_qua_text = 'XỈU'
    else:
        ket_qua = 'T' if tong > 10 else 'X'
        ket_qua_text = 'TÀI' if ket_qua == 'T' else 'XỈU'
    
    prediction_system.add_result(ket_qua)
    
    pred = prediction_system.get_final_prediction()
    pred_text = 'TÀI' if pred['prediction'] == 'T' else 'XỈU'
    conf = int(pred['confidence'] * 100)
    
    is_correct = pred['prediction'] == ket_qua
    status = '✅ ĐÚNG' if is_correct else '❌ SAI'
    
    return {
        'phien': phien,
        'd1': d1,
        'd2': d2,
        'd3': d3,
        'tong': tong,
        'ket_qua': ket_qua_text,
        'du_doan': pred_text,
        'do_tin_cay': conf,
        'status': status,
        'is_correct': is_correct,
        'ly_do': pred.get('reasons', [])[:3],
        'stats': prediction_system.get_stats()
    }

# ── BOT COMMANDS ────────────────────────────────────────

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    # Kiểm tra user
    is_valid, result = user_manager.check_user(user_id)
    
    if not is_valid:
        keyboard = [
            [InlineKeyboardButton("🔑 Đăng ký key", callback_data='register')],
            [InlineKeyboardButton("📱 Liên hệ admin", url='https://t.me/hoangquan280')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"🎲 *CHÀO {username}!*\n\n"
            f"❌ Bạn chưa được đăng ký sử dụng bot!\n"
            f"🆔 ID của bạn: `{user_id}`\n\n"
            f"📌 Vui lòng liên hệ admin để được cấp key.\n"
            f"🔑 Sau khi có key, gửi /register <key>",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    user_info = result
    expiry = datetime.fromisoformat(user_info['expiry']).strftime('%d/%m/%Y')
    
    await update.message.reply_text(
        f"🎲 *CHÀO {username}!*\n\n"
        f"✅ *Đã xác thực thành công!*\n"
        f"🆔 ID: `{user_id}`\n"
        f"👤 Vai trò: {user_info.get('role', 'user').upper()}\n"
        f"📅 Hạn key: {expiry}\n"
        f"📊 Số lần dùng: {user_info.get('total_requests', 0)}\n\n"
        f"📌 *Lệnh:*\n"
        f"/predict - Dự đoán phiên hiện tại\n"
        f"/stats - Thống kê chi tiết\n"
        f"/patterns - Các pattern phổ biến\n"
        f"/models - Hiệu suất các model\n"
        f"/live - Bật chế độ live\n"
        f"/help - Hướng dẫn\n"
        f"/info - Thông tin user\n\n"
        f"🔮 *Bot dự đoán Tài Xỉu với 150 thuật toán AI*",
        parse_mode='Markdown'
    )

# Register key
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    # Kiểm tra nếu đã có key
    is_valid, _ = user_manager.check_user(user_id)
    if is_valid:
        await update.message.reply_text("✅ Bạn đã có key rồi! Dùng /info để xem chi tiết.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"❌ Vui lòng nhập key!\n"
            f"📌 Cú pháp: `/register <key>`\n\n"
            f"🆔 ID của bạn: `{user_id}`\n"
            f"📱 Liên hệ admin để lấy key: @hoangquan280",
            parse_mode='Markdown'
        )
        return
    
    key = args[0]
    
    # Kiểm tra key trong hệ thống
    # Key có thể được tạo sẵn bởi admin, hoặc key tự động
    # Ở đây mình cho phép key là bất kỳ (admin sẽ tạo và gửi cho user)
    
    # Tạo user mới với key nhập vào
    success, result = user_manager.add_user(user_id, username, expiry_days=30, role='user')
    
    if success:
        # Cập nhật key cho user
        user_data = user_manager.users[str(user_id)]
        user_data['key'] = key
        user_manager.save_config()
        
        await update.message.reply_text(
            f"✅ *ĐĂNG KÝ THÀNH CÔNG!*\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"🔑 Key: `{key}`\n"
            f"📅 Hạn: 30 ngày\n\n"
            f"📌 Dùng /start để bắt đầu!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ {result}")

# Info user
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = user_manager.get_user_info(user_id)
    
    if not user_info:
        await update.message.reply_text("❌ Bạn chưa đăng ký! Dùng /register <key>")
        return
    
    expiry = datetime.fromisoformat(user_info['expiry'])
    is_expired = expiry < datetime.now()
    days_left = (expiry - datetime.now()).days
    
    msg = (
        f"👤 *THÔNG TIN USER*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{user_id}`\n"
        f"🔑 Key: `{user_info.get('key', 'N/A')}`\n"
        f"👤 Vai trò: {user_info.get('role', 'user').upper()}\n"
        f"📅 Ngày tạo: {user_info.get('created_at', 'N/A')[:10]}\n"
        f"📅 Hạn key: {expiry.strftime('%d/%m/%Y')}\n"
        f"⏳ Còn lại: {days_left} ngày\n"
        f"📊 Trạng thái: {'✅ Còn hạn' if not is_expired else '❌ Hết hạn'}\n"
        f"📈 Lượt dùng: {user_info.get('total_requests', 0)}\n"
        f"🕐 Hoạt động cuối: {user_info.get('last_active', 'Chưa')}"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# Predict
@require_auth
async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang lấy dữ liệu...")
    
    data = await fetch_history()
    if not data:
        await update.message.reply_text("❌ Không thể lấy dữ liệu từ API!")
        return
    
    result = process_data(data)
    if not result:
        await update.message.reply_text("❌ Không xử lý được dữ liệu!")
        return
    
    msg = (
        f"🎲 *PHIÊN #{result['phien']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 *Xúc xắc:* {result['d1']} - {result['d2']} - {result['d3']}\n"
        f"📊 *Tổng:* {result['tong']}\n"
        f"✅ *Kết quả:* {result['ket_qua']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔮 *Dự đoán:* {result['du_doan']}\n"
        f"📈 *Độ tin cậy:* {result['do_tin_cay']}%\n"
        f"📌 *Đánh giá:* {result['status']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    
    if result['ly_do']:
        msg += f"💡 *Lý do:*\n"
        for i, reason in enumerate(result['ly_do'], 1):
            msg += f"   {i}. {reason}\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Dự đoán lại", callback_data='predict')],
        [InlineKeyboardButton("📊 Thống kê", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)

# Stats
@require_auth
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_data = prediction_system.get_stats()
    
    msg = (
        f"📊 *THỐNG KÊ CHI TIẾT*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Tổng phiên:* {stats_data['total_sessions']}\n"
        f"🎯 *Tài:* {stats_data['tai_count']} ({stats_data['tai_percentage']:.1f}%)\n"
        f"🎯 *Xỉu:* {stats_data['xiu_count']} ({stats_data['xiu_percentage']:.1f}%)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Dự đoán đúng:* {stats_data['correct_predictions']}\n"
        f"❌ *Dự đoán sai:* {stats_data['wrong_predictions']}\n"
        f"📈 *Tỉ lệ chính xác:* {stats_data['prediction_accuracy']:.1f}%\n"
        f"🔥 *Streak hiện tại:* {stats_data['current_streak']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Biến động:* {stats_data['volatility']:.1f}%\n"
        f"🌀 *Entropy:* {stats_data['entropy']:.3f}\n"
        f"🧠 *Số model:* {stats_data['model_count']}\n"
        f"🧩 *Pattern:* {stats_data['pattern_count']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏰ *Cập nhật:* {datetime.now().strftime('%H:%M:%S')}"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# Patterns
@require_auth
async def patterns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    patterns_data = prediction_system.get_patterns()
    
    if not patterns_data:
        await update.message.reply_text("🧩 Chưa có pattern nào được ghi nhận!")
        return
    
    msg = "🧩 *TOP 50 PATTERN PHỔ BIẾN*\n━━━━━━━━━━━━━━━━━━\n"
    for i, p in enumerate(patterns_data[:20], 1):
        msg += f"{i}. `{p['pattern']}` → {p['next']} (acc: {p['accuracy']}) - {p['count']} lần\n"
    
    if len(patterns_data) > 20:
        msg += f"\n... và {len(patterns_data) - 20} pattern khác"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# Models
@require_auth
async def models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perf = prediction_system.get_detailed_performance()
    
    if not perf:
        await update.message.reply_text("🤖 Chưa có dữ liệu hiệu suất!")
        return
    
    sorted_models = sorted(perf.items(), key=lambda x: float(x[1]['accuracy'].replace('%', '')), reverse=True)[:15]
    
    msg = "🤖 *TOP 15 MODELS HIỆU SUẤT CAO NHẤT*\n━━━━━━━━━━━━━━━━━━\n"
    for i, (name, data) in enumerate(sorted_models, 1):
        msg += f"{i}. `{name}`\n"
        msg += f"   📈 Độ chính xác: {data['accuracy']}\n"
        msg += f"   📊 Tổng: {data['total']} | Streak: {data['streak']}\n"
        msg += f"   ⚖️ Trọng số: {data['weight']}\n"
        msg += f"   ─────────────────\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# Live
@require_auth
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    job_name = f"live_{chat_id}"
    current_jobs = context.job_queue.jobs()
    
    for job in current_jobs:
        if job.name == job_name:
            job.schedule_removal()
            await update.message.reply_text("🔄 Đã tắt chế độ live!")
            return
    
    context.job_queue.run_repeating(
        live_update,
        interval=FETCH_INTERVAL,
        first=1,
        name=job_name,
        chat_id=chat_id
    )
    
    await update.message.reply_text(
        f"🔄 *ĐÃ BẬT CHẾ ĐỘ LIVE!*\n"
        f"⏰ Cập nhật mỗi {FETCH_INTERVAL} giây\n"
        f"📌 Gửi /live để tắt",
        parse_mode='Markdown'
    )

async def live_update(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    data = await fetch_history()
    
    if not data:
        return
    
    result = process_data(data)
    if not result:
        return
    
    msg = (
        f"🎲 *PHIÊN #{result['phien']}*\n"
        f"🎯 {result['d1']}-{result['d2']}-{result['d3']} = {result['tong']}\n"
        f"📊 KQ: {result['ket_qua']} | 📈 DĐ: {result['du_doan']} ({result['do_tin_cay']}%)\n"
        f"📌 {result['status']}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

# Help
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 *HƯỚNG DẪN SỬ DỤNG*\n\n"
        "📌 /predict - Dự đoán phiên tiếp theo\n"
        "📊 /stats - Xem thống kê chi tiết\n"
        "🧩 /patterns - 50 pattern phổ biến nhất\n"
        "🤖 /models - Hiệu suất 150 models\n"
        "🔄 /live - Bật chế độ tự động cập nhật\n"
        "👤 /info - Thông tin user\n"
        "🔑 /register <key> - Đăng ký key\n"
        "❓ /help - Hiển thị hướng dẫn\n\n"
        "🔮 *Cập nhật mỗi 10 giây từ API LC79*",
        parse_mode='Markdown'
    )

# ── ADMIN COMMANDS ──────────────────────────────────────
async def admin_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền admin!")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "📌 Cú pháp: /add_user <user_id> <username> [days]\n"
            "Ví dụ: /add_user 123456789 hoangquan 30"
        )
        return
    
    target_id = int(args[0])
    username = args[1]
    days = int(args[2]) if len(args) > 2 else 30
    
    success, result = user_manager.add_user(target_id, username, expiry_days=days, role='user')
    
    if success:
        await update.message.reply_text(
            f"✅ *ĐÃ THÊM USER!*\n\n"
            f"🆔 ID: `{target_id}`\n"
            f"🔑 Key: `{result}`\n"
            f"👤 Username: {username}\n"
            f"📅 Hạn: {days} ngày",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ {result}")

async def admin_remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền admin!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("📌 Cú pháp: /remove_user <user_id>")
        return
    
    target_id = int(args[0])
    
    if user_manager.remove_user(target_id):
        await update.message.reply_text(f"✅ Đã xóa user {target_id}")
    else:
        await update.message.reply_text(f"❌ Không tìm thấy user {target_id}")

async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền admin!")
        return
    
    users = user_manager.list_users()
    
    if not users:
        await update.message.reply_text("📭 Chưa có user nào!")
        return
    
    msg = "👥 *DANH SÁCH USER*\n━━━━━━━━━━━━━━━━━━\n"
    for u in users:
        status = "✅" if not u['is_expired'] else "❌"
        msg += f"{status} `{u['user_id']}` - {u['username']}\n"
        msg += f"   Role: {u['role']} | Lượt: {u['total_requests']}\n"
        msg += f"   Key: `{u['key']}`\n"
        msg += f"   Hạn: {u['expiry'][:10]}\n"
        msg += f"   ─────────────────\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền admin!")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📌 Cú pháp: /extend <user_id> <days>")
        return
    
    target_id = int(args[0])
    days = int(args[1])
    
    success, result = user_manager.extend_expiry(target_id, days)
    
    if success:
        await update.message.reply_text(
            f"✅ Đã gia hạn user {target_id} thêm {days} ngày!\n"
            f"📅 Hạn mới: {result.strftime('%d/%m/%Y')}"
        )
    else:
        await update.message.reply_text(f"❌ {result}")

# ── CALLBACK ─────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'predict':
        await predict(update, context)
    elif query.data == 'stats':
        await stats(update, context)
    elif query.data == 'register':
        user_id = update.effective_user.id
        await query.edit_message_text(
            f"🔑 *ĐĂNG KÝ KEY*\n\n"
            f"🆔 ID của bạn: `{user_id}`\n\n"
            f"📌 Vui lòng liên hệ admin để lấy key:\n"
            f"📱 @hoangquan280\n\n"
            f"Sau khi có key, gửi lệnh:\n"
            f"`/register <key>`",
            parse_mode='Markdown'
        )

# ── MAIN ──────────────────────────────────────────────────
async def main():
    if not TOKEN:
        logger.error("❌ Không tìm thấy BOT_TOKEN trong .env!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("predict", predict))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("patterns", patterns))
    application.add_handler(CommandHandler("models", models))
    application.add_handler(CommandHandler("live", live))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("register", register))
    
    # Admin commands
    application.add_handler(CommandHandler("add_user", admin_add_user))
    application.add_handler(CommandHandler("remove_user", admin_remove_user))
    application.add_handler(CommandHandler("list_users", admin_list_users))
    application.add_handler(CommandHandler("extend", admin_extend))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🔄 Đang lấy dữ liệu lần đầu...")
    await fetch_history()
    
    logger.info("🚀 Bot đang chạy...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    asyncio.run(main())
