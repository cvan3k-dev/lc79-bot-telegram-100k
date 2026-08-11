import asyncio
import logging
import os
import aiohttp
import sys
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from prediction_system import UltraPredictionSystem
from config import user_manager, ADMIN_IDS
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ──────────────────────────────────────────────
TOKEN = os.getenv('BOT_TOKEN')
API_HISTORY = 'https://web-tool-4ej3.onrender.com/api/lc79/history'
FETCH_INTERVAL = 10
CACHE_FILE = 'cache_data.json'

# ── LOGGING ─────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── KHỞI TẠO HỆ THỐNG DỰ ĐOÁN ─────────────────────────
prediction_system = UltraPredictionSystem()
last_session = None
last_data = None
cache_data = None

# ── KIỂM TRA TOKEN ──────────────────────────────────────
if not TOKEN:
    logger.error("❌ KHÔNG TÌM THẤY BOT_TOKEN!")
    sys.exit(1)

logger.info(f"✅ Bot Token: {TOKEN[:10]}...")
logger.info(f"🧠 Đã khởi tạo {len(prediction_system.models)} models")

# ── QUẢN LÝ CACHE ──────────────────────────────────────
def load_cache():
    global cache_data
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                logger.info(f"✅ Đã tải cache: {len(cache_data.get('history', []))} phiên")
                return cache_data
    except Exception as e:
        logger.warning(f"⚠️ Không thể tải cache: {e}")
    return None

def save_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("💾 Đã lưu cache")
    except Exception as e:
        logger.warning(f"⚠️ Không thể lưu cache: {e}")

# ── LẤY DỮ LIỆU TỪ API ──────────────────────────────────
async def fetch_history():
    global last_session, last_data, cache_data
    
    try:
        logger.info("🔄 Đang lấy dữ liệu từ API...")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                API_HISTORY,
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=10
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') == 'OK':
                        items = data.get('data', [])
                        if items:
                            # Tìm phiên có kết quả đầy đủ
                            for item in items:
                                # Kiểm tra các key cần thiết
                                has_dice = all(k in item for k in ['d1', 'd2', 'd3'])
                                has_result = 'kết_quả' in item or 'ket_qua' in item
                                has_session = 'phiên' in item or 'phien' in item
                                
                                if has_dice and has_result and has_session:
                                    # Lưu cache
                                    cache_data = {'last_session': item.get('phiên', item.get('phien')), 'data': item, 'history': items}
                                    save_cache(cache_data)
                                    
                                    session_id = item.get('phiên', item.get('phien'))
                                    if session_id != last_session:
                                        last_session = session_id
                                        last_data = item
                                        logger.info(f"✅ Lấy dữ liệu thành công: #{session_id}")
                                        return item
                                    else:
                                        logger.info(f"⏳ Phiên #{session_id} đã xử lý")
                                        return None
    except Exception as e:
        logger.warning(f"⚠️ Lỗi fetch API: {e}")
    
    # Fallback: dùng cache
    if cache_data:
        logger.info("📦 Đang dùng dữ liệu cache...")
        valid = cache_data.get('data')
        if valid:
            session_id = valid.get('phiên', valid.get('phien'))
            if session_id != last_session:
                last_session = session_id
                last_data = valid
                logger.info(f"✅ Dùng cache: #{session_id}")
                return valid
    
    return None

# ── XỬ LÝ DỮ LIỆU ──────────────────────────────────────
def process_data(data):
    if not data:
        return None
    
    phien = data.get('phiên') or data.get('phien', '--')
    d1 = data.get('d1', 0)
    d2 = data.get('d2', 0)
    d3 = data.get('d3', 0)
    tong = data.get('tổng') or data.get('tong', d1 + d2 + d3)
    ket_qua_raw = data.get('kết_quả') or data.get('ket_qua', '')
    
    # Xác định kết quả
    if ket_qua_raw in ['tai', 'Tài', 'T', 't']:
        ket_qua = 'T'
        ket_qua_text = 'TÀI'
    elif ket_qua_raw in ['xiu', 'Xỉu', 'X', 'x']:
        ket_qua = 'X'
        ket_qua_text = 'XỈU'
    else:
        ket_qua = 'T' if tong > 10 else 'X'
        ket_qua_text = 'TÀI' if ket_qua == 'T' else 'XỈU'
    
    # Thêm vào hệ thống dự đoán
    prediction_system.add_result(ket_qua)
    
    # Lấy dự đoán
    pred = prediction_system.get_final_prediction()
    pred_text = 'TÀI' if pred['prediction'] == 'T' else 'XỈU'
    conf = int(pred['confidence'] * 100)
    
    # Đánh giá
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
        'ly_do': pred.get('reasons', [])[:3]
    }

# ── DECORATOR KIỂM TRA QUYỀN ───────────────────────────
def require_auth(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        is_valid, result = user_manager.check_user(user_id)
        
        if not is_valid:
            keyboard = [
                [InlineKeyboardButton("🔑 Đăng ký key", callback_data='register')],
                [InlineKeyboardButton("📱 Liên hệ admin", url='https://t.me/hoangquan280')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"{result}\n\n"
                f"🆔 ID của bạn: `{user_id}`",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

# ── BOT COMMANDS ────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    is_valid, result = user_manager.check_user(user_id)
    
    if not is_valid:
        keyboard = [
            [InlineKeyboardButton("🔑 Đăng ký key", callback_data='register')],
            [InlineKeyboardButton("📱 Liên hệ admin", url='https://t.me/hoangquan280')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"🎲 *CHÀO {username}!*\n\n"
            f"❌ Bạn chưa được đăng ký!\n"
            f"🆔 ID: `{user_id}`\n\n"
            f"📌 Liên hệ admin để lấy key.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    user_info = result
    expiry = datetime.fromisoformat(user_info['expiry']).strftime('%d/%m/%Y')
    
    await update.message.reply_text(
        f"🎲 *CHÀO {username}!*\n\n"
        f"✅ *Đã xác thực!*\n"
        f"🆔 ID: `{user_id}`\n"
        f"👤 Vai trò: {user_info.get('role', 'user').upper()}\n"
        f"📅 Hạn key: {expiry}\n"
        f"🧠 Số model: {len(prediction_system.models)}\n\n"
        f"📌 *Lệnh:*\n"
        f"/predict - Dự đoán\n"
        f"/stats - Thống kê\n"
        f"/patterns - Pattern\n"
        f"/models - Hiệu suất\n"
        f"/live - Live update\n"
        f"/info - Thông tin user\n"
        f"/help - Hướng dẫn",
        parse_mode='Markdown'
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    is_valid, _ = user_manager.check_user(user_id)
    if is_valid:
        await update.message.reply_text("✅ Bạn đã có key! Dùng /info để xem.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"❌ Cú pháp: `/register <key>`\n"
            f"🆔 ID: `{user_id}`",
            parse_mode='Markdown'
        )
        return
    
    key = args[0]
    success, result = user_manager.add_user(user_id, username, expiry_days=30, role='user')
    
    if success:
        user_data = user_manager.users[str(user_id)]
        user_data['key'] = key
        user_manager.save_config()
        await update.message.reply_text(
            f"✅ *ĐĂNG KÝ THÀNH CÔNG!*\n"
            f"🔑 Key: `{key}`\n"
            f"📅 Hạn: 30 ngày\n"
            f"📌 Dùng /predict để bắt đầu!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ {result}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = user_manager.get_user_info(user_id)
    
    if not user_info:
        await update.message.reply_text("❌ Chưa đăng ký! Dùng /register <key>")
        return
    
    expiry = datetime.fromisoformat(user_info['expiry'])
    days_left = (expiry - datetime.now()).days
    
    msg = (
        f"👤 *THÔNG TIN USER*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{user_id}`\n"
        f"🔑 Key: `{user_info.get('key', 'N/A')}`\n"
        f"👤 Role: {user_info.get('role', 'user').upper()}\n"
        f"📅 Hạn: {expiry.strftime('%d/%m/%Y')}\n"
        f"⏳ Còn: {days_left} ngày\n"
        f"📈 Lượt dùng: {user_info.get('total_requests', 0)}"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

@require_auth
async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang lấy dữ liệu từ API...")
    
    data = await fetch_history()
    if not data:
        await update.message.reply_text(
            "❌ Không thể lấy dữ liệu!\n"
            "🔄 Đang thử lại...\n"
            "📌 Kiểm tra API: https://web-tool-4ej3.onrender.com/api/lc79/history"
        )
        return
    
    result = process_data(data)
    if not result:
        await update.message.reply_text("❌ Lỗi xử lý dữ liệu!")
        return
    
    msg = (
        f"🎲 *PHIÊN #{result['phien']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 {result['d1']}-{result['d2']}-{result['d3']} = {result['tong']}\n"
        f"✅ KQ: {result['ket_qua']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔮 *Dự đoán:* {result['du_doan']}\n"
        f"📈 Độ tin cậy: {result['do_tin_cay']}%\n"
        f"📌 {result['status']}\n"
    )
    
    if result['ly_do']:
        msg += f"\n💡 Lý do:\n"
        for i, reason in enumerate(result['ly_do'], 1):
            msg += f"   {i}. {reason}\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Dự đoán lại", callback_data='predict')],
        [InlineKeyboardButton("📊 Thống kê", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)

@require_auth
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_data = prediction_system.get_stats()
    
    msg = (
        f"📊 *THỐNG KÊ*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Tổng phiên: {stats_data['total_sessions']}\n"
        f"🎯 Tài: {stats_data['tai_count']} ({stats_data['tai_percentage']:.1f}%)\n"
        f"🎯 Xỉu: {stats_data['xiu_count']} ({stats_data['xiu_percentage']:.1f}%)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Đúng: {stats_data['correct_predictions']}\n"
        f"❌ Sai: {stats_data['wrong_predictions']}\n"
        f"📈 Tỉ lệ: {stats_data['prediction_accuracy']:.1f}%\n"
        f"🔥 Streak: {stats_data['current_streak']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🧠 Model: {stats_data['model_count']}\n"
        f"🧩 Pattern: {stats_data['pattern_count']}"
    )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

@require_auth
async def patterns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    patterns_data = prediction_system.get_patterns()
    
    if not patterns_data:
        await update.message.reply_text("🧩 Chưa có pattern nào!")
        return
    
    msg = "🧩 *TOP PATTERN*\n━━━━━━━━━━━━━━━━━━\n"
    for i, p in enumerate(patterns_data[:15], 1):
        msg += f"{i}. `{p['pattern']}` → {p['next']} (acc: {p['accuracy']}) - {p['count']} lần\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

@require_auth
async def models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perf = prediction_system.get_detailed_performance()
    
    if not perf:
        await update.message.reply_text("🤖 Chưa có dữ liệu hiệu suất!")
        return
    
    sorted_models = sorted(perf.items(), key=lambda x: float(x[1]['accuracy'].replace('%', '')), reverse=True)[:10]
    
    msg = "🤖 *TOP 10 MODELS*\n━━━━━━━━━━━━━━━━━━\n"
    for i, (name, data) in enumerate(sorted_models, 1):
        msg += f"{i}. `{name}`\n"
        msg += f"   📈 {data['accuracy']} | 📊 {data['total']} | ⚖️ {data['weight']}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

@require_auth
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if context.job_queue is None:
        await update.message.reply_text("❌ Live mode không khả dụng!")
        return
    
    job_name = f"live_{chat_id}"
    current_jobs = context.job_queue.jobs() if context.job_queue else []
    
    for job in current_jobs:
        if job.name == job_name:
            job.schedule_removal()
            await update.message.reply_text("🔄 Đã tắt live!")
            return
    
    context.job_queue.run_repeating(
        live_update,
        interval=FETCH_INTERVAL,
        first=1,
        name=job_name,
        chat_id=chat_id
    )
    
    await update.message.reply_text(
        f"🔄 *LIVE ĐÃ BẬT!*\n"
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
        f"🎲 #{result['phien']}\n"
        f"🎯 {result['d1']}-{result['d2']}-{result['d3']}\n"
        f"📊 {result['ket_qua']} | 🔮 {result['du_doan']} ({result['do_tin_cay']}%)\n"
        f"📌 {result['status']}"
    )
    
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 *HƯỚNG DẪN*\n\n"
        "/predict - Dự đoán phiên hiện tại\n"
        "/stats - Thống kê chi tiết\n"
        "/patterns - 50 pattern phổ biến\n"
        "/models - Hiệu suất 150 models\n"
        "/live - Bật live update\n"
        "/info - Thông tin user\n"
        "/register <key> - Đăng ký key\n\n"
        f"📡 API: {API_HISTORY}",
        parse_mode='Markdown'
    )

# ── ADMIN COMMANDS ──────────────────────────────────────
async def admin_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📌 /add_user <user_id> <username> [days]")
        return
    
    target_id = int(args[0])
    username = args[1]
    days = int(args[2]) if len(args) > 2 else 30
    
    success, result = user_manager.add_user(target_id, username, expiry_days=days, role='user')
    
    if success:
        await update.message.reply_text(
            f"✅ *ĐÃ THÊM USER!*\n"
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
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("📌 /remove_user <user_id>")
        return
    
    target_id = int(args[0])
    
    if user_manager.remove_user(target_id):
        await update.message.reply_text(f"✅ Đã xóa user {target_id}")
    else:
        await update.message.reply_text(f"❌ Không tìm thấy user {target_id}")

async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    
    users = user_manager.list_users()
    
    if not users:
        await update.message.reply_text("📭 Chưa có user nào!")
        return
    
    msg = "👥 *DANH SÁCH USER*\n━━━━━━━━━━━━━━━━━━\n"
    for u in users[:10]:
        status = "✅" if not u['is_expired'] else "❌"
        msg += f"{status} `{u['user_id']}` - {u['username']}\n"
        msg += f"   Role: {u['role']} | Key: `{u['key']}`\n"
        msg += f"   Hạn: {u['expiry'][:10]} | Lượt: {u['total_requests']}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📌 /extend <user_id> <days>")
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
            f"🔑 *ĐĂNG KÝ*\n\n"
            f"🆔 ID: `{user_id}`\n\n"
            f"📱 Liên hệ admin: @hoangquan280\n"
            f"Sau đó gửi: `/register <key>`",
            parse_mode='Markdown'
        )

# ── MAIN ──────────────────────────────────────────────────
async def main():
    logger.info("🚀 Đang khởi động bot...")
    
    # Tải cache
    load_cache()
    
    # Lấy dữ liệu lần đầu
    await fetch_history()
    
    # Tạo application
    app = Application.builder().token(TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("predict", predict))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("patterns", patterns))
    app.add_handler(CommandHandler("models", models))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("register", register))
    
    # Admin commands
    app.add_handler(CommandHandler("add_user", admin_add_user))
    app.add_handler(CommandHandler("remove_user", admin_remove_user))
    app.add_handler(CommandHandler("list_users", admin_list_users))
    app.add_handler(CommandHandler("extend", admin_extend))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Xóa webhook
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Đã xóa webhook")
    
    # Khởi tạo và bắt đầu polling thủ công
    await app.initialize()
    await app.start()
    
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=30
    )
    logger.info("🔄 Bot đang chạy polling...")
    
    # Giữ bot chạy
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("🛑 Đang dừng bot...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

# ── ENTRY POINT ──────────────────────────────────────────
if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(main())
        loop.run_forever()
    except RuntimeError:
        asyncio.run(main())
