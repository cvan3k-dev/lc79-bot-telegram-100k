import asyncio
import logging
import os
import aiohttp
import sys
import json
import random
import hashlib
import time
from collections import deque
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ──────────────────────────────────────────────
TOKEN = os.getenv('BOT_TOKEN')
API_HISTORY = 'https://web-tool-4ej3.onrender.com/api/lc79/history'
API_HISTORY_BACKUP = 'https://corsproxy.io/?' + API_HISTORY
FETCH_INTERVAL = 10
CACHE_FILE = 'cache_data.json'
CONFIG_FILE = 'users_config.json'
ADMIN_IDS = [5888859004]

# ── LOGGING ─────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error("❌ KHÔNG TÌM THẤY BOT_TOKEN!")
    sys.exit(1)

logger.info(f"✅ Bot Token: {TOKEN[:10]}...")

# ── USER MANAGER ──────────────────────────────────────────
class UserManager:
    # ... (giữ nguyên code cũ)
    pass

# ── PREDICTION SYSTEM ──────────────────────────────────
class UltraPredictionSystem:
    # ... (giữ nguyên code cũ)
    pass

# ═══════════════════════════════════════════════════════════
# KHỞI TẠO
# ═══════════════════════════════════════════════════════════

user_manager = UserManager()
for admin_id in ADMIN_IDS:
    if str(admin_id) not in user_manager.users:
        user_manager.add_user(admin_id, 'admin', expiry_days=365, role='admin')
        logger.info(f"✅ Đã thêm admin: {admin_id}")

prediction_system = UltraPredictionSystem()
logger.info(f"🧠 Đã khởi tạo {len(prediction_system.models)} models")

last_session = None
last_data = None
cache_data = None

# ── FUNCTIONS ──────────────────────────────────────────────

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

# ── LẤY DỮ LIỆU TỪ API (CHỈ LẤY PHIÊN MỚI NHẤT) ─────

async def fetch_history():
    global last_session, last_data, cache_data
    
    apis_to_try = [
        API_HISTORY,
        API_HISTORY_BACKUP,
    ]
    
    for api_url in apis_to_try:
        try:
            logger.info(f"🔄 Đang gọi API: {api_url[:50]}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    headers={
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    },
                    timeout=26  # 🔥 TĂNG TIMEOUT
                ) as response:
                    
                    logger.info(f"📡 Status: {response.status}")
                    
                    if response.status == 200:
                        text = await response.text()
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️ Không parse được JSON")
                            continue
                        
                        if data.get('status') == 'OK':
                            items = data.get('data', [])
                            logger.info(f"📊 Nhận được {len(items)} phiên")
                            
                            if items:
                                # 🔥 CHỈ LẤY PHIÊN ĐẦU TIÊN (MỚI NHẤT)
                                first_item = items[0]
                                
                                # Kiểm tra dữ liệu hợp lệ
                                has_dice = all(k in first_item for k in ['d1', 'd2', 'd3'])
                                has_result = 'kết_quả' in first_item or 'ket_qua' in first_item
                                has_session = 'phiên' in first_item or 'phien' in first_item
                                
                                if has_dice and has_result and has_session:
                                    session_id = first_item.get('phiên', first_item.get('phien'))
                                    
                                    # Lưu cache (chỉ 10 phiên gần nhất)
                                    cache_data = {
                                        'last_session': session_id,
                                        'data': first_item,
                                        'history': items[:10]
                                    }
                                    save_cache(cache_data)
                                    
                                    if session_id != last_session:
                                        last_session = session_id
                                        last_data = first_item
                                        logger.info(f"✅ Lấy dữ liệu thành công: #{session_id}")
                                        return first_item
                                    else:
                                        logger.info(f"⏳ Phiên #{session_id} đã xử lý")
                                        return None
                                else:
                                    logger.warning(f"⚠️ Phiên không đủ dữ liệu: {list(first_item.keys())}")
                        else:
                            logger.warning(f"⚠️ API status: {data.get('status')}")
                    else:
                        logger.warning(f"⚠️ HTTP {response.status}")
                        
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Timeout (30s): {api_url}")
        except aiohttp.ClientError as e:
            logger.warning(f"⚠️ Client error: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Lỗi: {e}")
    
    # FALLBACK: Dùng cache
    if cache_data:
        logger.info("📦 Đang dùng cache...")
        valid = cache_data.get('data')
        if valid:
            session_id = valid.get('phiên', valid.get('phien'))
            if session_id != last_session:
                last_session = session_id
                last_data = valid
                logger.info(f"✅ Dùng cache: #{session_id}")
                return valid
    
   
def process_data(data):
    if not data:
        return None
    phien = data.get('phiên') or data.get('phien', '--')
    d1 = data.get('d1', 0)
    d2 = data.get('d2', 0)
    d3 = data.get('d3', 0)
    tong = data.get('tổng') or data.get('tong', d1 + d2 + d3)
    ket_qua_raw = data.get('kết_quả') or data.get('ket_qua', '')
    
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
        'ly_do': pred.get('reasons', [])[:3]
    }

def require_auth(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        is_valid, result = user_manager.check_user(user_id)
        if not is_valid:
            keyboard = [[InlineKeyboardButton("🔑 Đăng ký key", callback_data='register')], [InlineKeyboardButton("📱 Liên hệ admin", url='https://t.me/hoangquan280')]]
            await update.message.reply_text(f"{result}\n\n🆔 ID: `{user_id}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ═══════════════════════════════════════════════════════════
# BOT COMMANDS
# ═══════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    is_valid, result = user_manager.check_user(user_id)
    if not is_valid:
        keyboard = [[InlineKeyboardButton("🔑 Đăng ký key", callback_data='register')], [InlineKeyboardButton("📱 Liên hệ admin", url='https://t.me/hoangquan280')]]
        await update.message.reply_text(f"🎲 *CHÀO {username}!*\n\n❌ Bạn chưa được đăng ký!\n🆔 ID: `{user_id}`\n\n📌 Liên hệ admin để lấy key.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    user_info = result
    expiry = datetime.fromisoformat(user_info['expiry']).strftime('%d/%m/%Y')
    await update.message.reply_text(f"🎲 *CHÀO {username}!*\n\n✅ *Đã xác thực!*\n🆔 ID: `{user_id}`\n👤 Vai trò: {user_info.get('role', 'user').upper()}\n📅 Hạn key: {expiry}\n🧠 Số model: {len(prediction_system.models)}\n\n📌 *Lệnh:*\n/predict - Dự đoán\n/stats - Thống kê\n/patterns - Pattern\n/models - Hiệu suất\n/live - Live update\n/info - Thông tin user\n/help - Hướng dẫn", parse_mode='Markdown')

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    is_valid, _ = user_manager.check_user(user_id)
    if is_valid:
        await update.message.reply_text("✅ Bạn đã có key! Dùng /info để xem.")
        return
    args = context.args
    if not args:
        await update.message.reply_text(f"❌ Cú pháp: `/register <key>`\n🆔 ID: `{user_id}`", parse_mode='Markdown')
        return
    key = args[0]
    success, result = user_manager.add_user(user_id, username, expiry_days=30, role='user')
    if success:
        user_data = user_manager.users[str(user_id)]
        user_data['key'] = key
        user_manager.save_config()
        await update.message.reply_text(f"✅ *ĐĂNG KÝ THÀNH CÔNG!*\n🔑 Key: `{key}`\n📅 Hạn: 30 ngày\n📌 Dùng /predict để bắt đầu!", parse_mode='Markdown')
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
    await update.message.reply_text(f"👤 *THÔNG TIN USER*\n━━━━━━━━━━━━━━━━━━\n🆔 ID: `{user_id}`\n🔑 Key: `{user_info.get('key', 'N/A')}`\n👤 Role: {user_info.get('role', 'user').upper()}\n📅 Hạn: {expiry.strftime('%d/%m/%Y')}\n⏳ Còn: {days_left} ngày\n📈 Lượt dùng: {user_info.get('total_requests', 0)}", parse_mode='Markdown')

@require_auth
async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Đang lấy dữ liệu từ API (có thể mất 10-20 giây)...")
    
    data = await fetch_history()
    if not data:
        await msg.edit_text("❌ Không thể lấy dữ liệu!\n🔄 Đang thử lại...\n📌 API: https://web-tool-4ej3.onrender.com/api/lc79/history")
        return
    
    result = process_data(data)
    if not result:
        await msg.edit_text("❌ Lỗi xử lý dữ liệu!")
        return
    
    text = f"🎲 *PHIÊN #{result['phien']}*\n━━━━━━━━━━━━━━━━━━\n🎯 {result['d1']}-{result['d2']}-{result['d3']} = {result['tong']}\n✅ KQ: {result['ket_qua']}\n━━━━━━━━━━━━━━━━━━\n🔮 *Dự đoán:* {result['du_doan']}\n📈 Độ tin cậy: {result['do_tin_cay']}%\n📌 {result['status']}\n"
    if result['ly_do']:
        text += f"\n💡 Lý do:\n"
        for i, reason in enumerate(result['ly_do'], 1):
            text += f"   {i}. {reason}\n"
    
    keyboard = [[InlineKeyboardButton("🔄 Dự đoán lại", callback_data='predict')], [InlineKeyboardButton("📊 Thống kê", callback_data='stats')]]
    await msg.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

@require_auth
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_data = prediction_system.get_stats()
    await update.message.reply_text(f"📊 *THỐNG KÊ*\n━━━━━━━━━━━━━━━━━━\n📌 Tổng phiên: {stats_data['total_sessions']}\n🎯 Tài: {stats_data['tai_count']} ({stats_data['tai_percentage']:.1f}%)\n🎯 Xỉu: {stats_data['xiu_count']} ({stats_data['xiu_percentage']:.1f}%)\n━━━━━━━━━━━━━━━━━━\n✅ Đúng: {stats_data['correct_predictions']}\n❌ Sai: {stats_data['wrong_predictions']}\n📈 Tỉ lệ: {stats_data['prediction_accuracy']:.1f}%\n🔥 Streak: {stats_data['current_streak']}\n━━━━━━━━━━━━━━━━━━\n🧠 Model: {stats_data['model_count']}\n🧩 Pattern: {stats_data['pattern_count']}", parse_mode='Markdown')

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
        msg += f"{i}. `{name}`\n   📈 {data['accuracy']} | 📊 {data['total']} | ⚖️ {data['weight']}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

@require_auth
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.job_queue is None:
        await update.message.reply_text("❌ Live mode không khả dụng!")
        return
    job_name = f"live_{chat_id}"
    for job in context.job_queue.jobs():
        if job.name == job_name:
            job.schedule_removal()
            await update.message.reply_text("🔄 Đã tắt live!")
            return
    context.job_queue.run_repeating(live_update, interval=FETCH_INTERVAL, first=1, name=job_name, chat_id=chat_id)
    await update.message.reply_text(f"🔄 *LIVE ĐÃ BẬT!*\n⏰ Cập nhật mỗi {FETCH_INTERVAL} giây\n📌 Gửi /live để tắt", parse_mode='Markdown')

async def live_update(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    data = await fetch_history()
    if not data:
        return
    result = process_data(data)
    if not result:
        return
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎲 #{result['phien']}\n🎯 {result['d1']}-{result['d2']}-{result['d3']}\n📊 {result['ket_qua']} | 🔮 {result['du_doan']} ({result['do_tin_cay']}%)\n📌 {result['status']}",
        parse_mode='Markdown'
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎲 *HƯỚNG DẪN*\n\n/predict - Dự đoán phiên hiện tại\n/stats - Thống kê chi tiết\n/patterns - 50 pattern phổ biến\n/models - Hiệu suất 150 models\n/live - Bật live update\n/info - Thông tin user\n/register <key> - Đăng ký key\n\n📡 API: https://web-tool-4ej3.onrender.com/api/lc79/history", parse_mode='Markdown')

# ── ADMIN ──────────────────────────────────────────────────

async def admin_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📌 /add_user <user_id> <username> [days]")
        return
    target_id, username, days = int(args[0]), args[1], int(args[2]) if len(args) > 2 else 30
    success, result = user_manager.add_user(target_id, username, expiry_days=days, role='user')
    await update.message.reply_text(f"✅ *ĐÃ THÊM USER!*\n🆔 ID: `{target_id}`\n🔑 Key: `{result}`\n👤 Username: {username}\n📅 Hạn: {days} ngày" if success else f"❌ {result}", parse_mode='Markdown')

async def admin_remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    args = context.args
    if not args:
        await update.message.reply_text("📌 /remove_user <user_id>")
        return
    target_id = int(args[0])
    await update.message.reply_text(f"✅ Đã xóa user {target_id}" if user_manager.remove_user(target_id) else f"❌ Không tìm thấy user {target_id}")

async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    users = user_manager.list_users()
    if not users:
        await update.message.reply_text("📭 Chưa có user nào!")
        return
    msg = "👥 *DANH SÁCH USER*\n━━━━━━━━━━━━━━━━━━\n"
    for u in users[:10]:
        status = "✅" if not u['is_expired'] else "❌"
        msg += f"{status} `{u['user_id']}` - {u['username']}\n   Role: {u['role']} | Key: `{u['key']}`\n   Hạn: {u['expiry'][:10]} | Lượt: {u['total_requests']}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📌 /extend <user_id> <days>")
        return
    target_id, days = int(args[0]), int(args[1])
    success, result = user_manager.extend_expiry(target_id, days)
    await update.message.reply_text(f"✅ Đã gia hạn user {target_id} thêm {days} ngày!\n📅 Hạn mới: {result.strftime('%d/%m/%Y')}" if success else f"❌ {result}")

# ── CALLBACK ─────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'predict':
        await predict(update, context)
    elif query.data == 'stats':
        await stats(update, context)
    elif query.data == 'register':
        await query.edit_message_text(f"🔑 *ĐĂNG KÝ*\n\n🆔 ID: `{update.effective_user.id}`\n\n📱 Liên hệ admin: @hoangquan280\nSau đó gửi: `/register <key>`", parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

async def main():
    logger.info("🚀 Đang khởi động bot...")
    load_cache()
    await fetch_history()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("predict", predict))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("patterns", patterns))
    app.add_handler(CommandHandler("models", models))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("add_user", admin_add_user))
    app.add_handler(CommandHandler("remove_user", admin_remove_user))
    app.add_handler(CommandHandler("list_users", admin_list_users))
    app.add_handler(CommandHandler("extend", admin_extend))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Đã xóa webhook")
    
    await app.initialize()
    await app.start()
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            await app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                poll_interval=1.0,
                timeout=30
            )
            logger.info("🔄 Bot đang chạy polling...")
            break
        except Exception as e:
            if "Conflict" in str(e) and attempt < max_retries - 1:
                logger.warning(f"⚠️ Conflict! Retry {attempt+1}/{max_retries} sau 5s...")
                await asyncio.sleep(5)
                await app.bot.delete_webhook(drop_pending_updates=True)
            else:
                raise
    
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("🛑 Đang dừng bot...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot đã dừng")
    finally:
        loop.close()
        logger.info("✅ Đã đóng event loop")
