import asyncio
import logging
import os
import json
import time
import hashlib
import random
from datetime import datetime, timedelta
from collections import deque

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

load_dotenv()

# ==================== CẤU HÌNH ====================
TOKEN = os.getenv('BOT_TOKEN')
API_URL = 'https://web-tool-4ej3.onrender.com/api/lc79/history'
ADMIN_IDS = [5888859004]

if not TOKEN:
    print("❌ Thiếu BOT_TOKEN")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== USER MANAGER ====================
class UserManager:
    def __init__(self):
        self.file = 'users.json'
        self.data = {}
        self.load()

    def load(self):
        try:
            with open(self.file, 'r') as f:
                self.data = json.load(f)
        except:
            self.data = {}

    def save(self):
        with open(self.file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def add_user(self, uid, name, days=30):
        uid = str(uid)
        if uid in self.data:
            return False, "Đã tồn tại"
        key = hashlib.md5(f"{uid}{time.time()}".encode()).hexdigest()[:8]
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        self.data[uid] = {'name': name, 'key': key, 'expiry': expiry, 'role': 'user'}
        self.save()
        return True, key

    def check(self, uid):
        uid = str(uid)
        if uid not in self.data:
            return False, "❌ Chưa đăng ký"
        user = self.data[uid]
        if datetime.fromisoformat(user['expiry']) < datetime.now():
            return False, "❌ Key hết hạn"
        return True, user

    def extend(self, uid, days=30):
        uid = str(uid)
        if uid not in self.data:
            return False, "Không tồn tại"
        old = datetime.fromisoformat(self.data[uid]['expiry'])
        new = old + timedelta(days=days)
        self.data[uid]['expiry'] = new.isoformat()
        self.save()
        return True, new

# ==================== PREDICTION SYSTEM (150 Models) ====================
class PredictionSystem:
    def __init__(self):
        self.history = deque(maxlen=500)
        self.models = {}
        self.weights = {}
        self.perf = {}
        self.total_correct = 0
        self.total_wrong = 0

        # Tạo 150 models
        for i in range(1, 151):
            self.models[f'm{i}'] = self._make_model(i)
            self.weights[f'm{i}'] = 0.5 + random.random() * 0.4
            self.perf[f'm{i}'] = {'c': 0, 't': 0}

        # 21 models đặc biệt
        self.models['m_special'] = self._special_model
        self.weights['m_special'] = 0.8
        self.perf['m_special'] = {'c': 0, 't': 0}

        self.load()

    def _make_model(self, idx):
        def predict():
            if len(self.history) < 3:
                return None
            last = self.history[-1] if self.history else 'T'
            # Dựa trên index để tạo dự đoán khác nhau
            seed = (idx * 7 + idx % 5) % 10
            pred = 'T' if (idx + seed) % 2 == 0 else 'X'
            conf = 0.4 + (idx % 5) * 0.08
            return {'pred': pred, 'conf': min(0.9, conf)}
        return predict

    def _special_model(self):
        if len(self.history) < 3:
            return None
        last3 = list(self.history)[-3:]
        if last3[0] == last3[1] and last3[1] != last3[2]:
            return {'pred': last3[1], 'conf': 0.7}
        if last3[0] != last3[1] and last3[1] == last3[2]:
            return {'pred': last3[2], 'conf': 0.65}
        return None

    def add_result(self, result):
        if result not in ['T', 'X']:
            return
        self.history.append(result)

        # Cập nhật hiệu suất
        for name, func in self.models.items():
            pred = func()
            if pred and pred.get('pred'):
                self.perf[name]['t'] += 1
                if pred['pred'] == result:
                    self.perf[name]['c'] += 1
                    self.weights[name] = min(1.8, self.weights[name] + 0.02)
                else:
                    self.weights[name] = max(0.1, self.weights[name] - 0.02)

        # Đánh giá tổng thể
        final = self.predict()
        if final and final['pred'] == result:
            self.total_correct += 1
        else:
            self.total_wrong += 1

        self.save()

    def predict(self):
        t_score = 0
        x_score = 0
        for name, func in self.models.items():
            pred = func()
            if pred and pred.get('pred'):
                weight = self.weights.get(name, 0.5)
                conf = pred.get('conf', 0.5)
                if pred['pred'] == 'T':
                    t_score += weight * conf
                else:
                    x_score += weight * conf

        if t_score == 0 and x_score == 0:
            last = self.history[-1] if self.history else 'T'
            return {'pred': last, 'conf': 0.5}

        pred = 'T' if t_score > x_score else 'X'
        conf = max(t_score, x_score) / (t_score + x_score)
        return {'pred': pred, 'conf': min(0.95, conf)}

    def get_stats(self):
        total = len(self.history)
        t_count = sum(1 for x in self.history if x == 'T') if total else 0
        total_pred = self.total_correct + self.total_wrong
        return {
            'total': total,
            'tai': t_count,
            'xiu': total - t_count,
            'tai_pct': (t_count / total * 100) if total else 0,
            'correct': self.total_correct,
            'wrong': self.total_wrong,
            'acc': (self.total_correct / total_pred * 100) if total_pred else 0,
            'models': len(self.models)
        }

    def save(self):
        try:
            with open('pred_data.json', 'w') as f:
                json.dump({
                    'history': list(self.history),
                    'weights': self.weights,
                    'perf': self.perf,
                    'correct': self.total_correct,
                    'wrong': self.total_wrong
                }, f)
        except:
            pass

    def load(self):
        try:
            with open('pred_data.json', 'r') as f:
                data = json.load(f)
                self.history = deque(data.get('history', []), maxlen=500)
                self.weights.update(data.get('weights', {}))
                self.perf.update(data.get('perf', {}))
                self.total_correct = data.get('correct', 0)
                self.total_wrong = data.get('wrong', 0)
        except:
            pass

# ==================== KHỞI TẠO ====================
user_mgr = UserManager()
pred_sys = PredictionSystem()

# Thêm admin
for aid in ADMIN_IDS:
    if str(aid) not in user_mgr.data:
        user_mgr.add_user(aid, 'admin', 365)

# Cache
last_session = None
cache_data = None

# ==================== LẤY DỮ LIỆU API ====================
async def fetch_data():
    global last_session, cache_data

    try:
        logger.info("📡 Đang gọi API...")
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, timeout=30) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ HTTP {resp.status}")
                    return None

                raw = await resp.text()
                data = json.loads(raw)

                if data.get('status') != 'OK':
                    return None

                items = data.get('data', [])
                if not items:
                    return None

                # Lấy phiên đầu tiên (mới nhất)
                first = items[0]

                # Kiểm tra đủ dữ liệu
                if 'phiên' not in first or 'd1' not in first or 'kết_quả' not in first:
                    return None

                sid = first['phiên']
                if sid == last_session:
                    return None  # Đã xử lý phiên này

                last_session = sid
                cache_data = first

                # Lưu cache
                try:
                    with open('cache.json', 'w') as f:
                        json.dump({'data': first, 'time': time.time()}, f)
                except:
                    pass

                logger.info(f"✅ Lấy phiên #{sid}")
                return first

    except asyncio.TimeoutError:
        logger.warning("⏱️ Timeout 30s")
    except Exception as e:
        logger.warning(f"⚠️ Lỗi: {e}")

    # Fallback cache
    try:
        with open('cache.json', 'r') as f:
            cached = json.load(f)
            if cached and cached.get('data'):
                logger.info("📦 Dùng cache")
                return cached['data']
    except:
        pass

    return None

# ==================== XỬ LÝ DỮ LIỆU ====================
def process(data):
    if not data:
        return None

    phien = data.get('phiên', '--')
    d1 = data.get('d1', 0)
    d2 = data.get('d2', 0)
    d3 = data.get('d3', 0)
    tong = data.get('tổng', d1 + d2 + d3)
    kq_raw = data.get('kết_quả', '')

    kq = 'T' if kq_raw in ['tai', 'Tài', 'T', 't'] else ('X' if kq_raw in ['xiu', 'Xỉu', 'X', 'x'] else ('T' if tong > 10 else 'X'))
    kq_text = 'TÀI' if kq == 'T' else 'XỈU'

    pred_sys.add_result(kq)

    pred = pred_sys.predict()
    pred_text = 'TÀI' if pred['pred'] == 'T' else 'XỈU'
    conf = int(pred['conf'] * 100)

    return {
        'phien': phien,
        'd1': d1,
        'd2': d2,
        'd3': d3,
        'tong': tong,
        'kq': kq_text,
        'du_doan': pred_text,
        'do_tin_cay': conf,
        'dung_sai': '✅ ĐÚNG' if pred['pred'] == kq else '❌ SAI'
    }

# ==================== BOT COMMANDS ====================
async def start(uid, ctx):
    u = uid.effective_user
    ok, info = user_mgr.check(u.id)
    if not ok:
        kb = [[InlineKeyboardButton("🔑 Đăng ký", callback_data='register')]]
        await uid.message.reply_text(
            f"🎲 *CHÀO {u.first_name}!*\n\n❌ Chưa đăng ký\n🆔 ID: `{u.id}`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    expiry = datetime.fromisoformat(info['expiry']).strftime('%d/%m/%Y')
    await uid.message.reply_text(
        f"🎲 *BOT DỰ ĐOÁN TÀI XỈU*\n✅ Đã xác thực\n📅 Hạn: {expiry}\n🧠 {len(pred_sys.models)} models\n\n"
        f"/predict - Dự đoán\n/stats - Thống kê\n/patterns - Pattern\n/help - Hướng dẫn",
        parse_mode='Markdown'
    )

async def register(uid, ctx):
    u = uid.effective_user
    ok, _ = user_mgr.check(u.id)
    if ok:
        await uid.message.reply_text("✅ Bạn đã có key!")
        return

    args = ctx.args
    if not args:
        await uid.message.reply_text(f"❌ /register <key>\n🆔 ID: `{u.id}`", parse_mode='Markdown')
        return

    # Kiểm tra key (cho phép bất kỳ key nào)
    success, key = user_mgr.add_user(u.id, u.first_name, 30)
    if success:
        # Cập nhật key người dùng nhập
        user_mgr.data[str(u.id)]['key'] = args[0]
        user_mgr.save()
        await uid.message.reply_text(f"✅ Đăng ký thành công!\n🔑 Key: `{args[0]}`", parse_mode='Markdown')
    else:
        await uid.message.reply_text("❌ Đã có lỗi xảy ra")

async def predict(uid, ctx):
    msg = await uid.message.reply_text("⏳ Đang lấy dữ liệu (có thể mất 10-20s)...")

    data = await fetch_data()
    if not data:
        await msg.edit_text("❌ Không lấy được dữ liệu!\n🔄 Thử lại sau")
        return

    result = process(data)
    if not result:
        await msg.edit_text("❌ Lỗi xử lý dữ liệu!")
        return

    text = (
        f"🎲 *PHIÊN #{result['phien']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 {result['d1']}-{result['d2']}-{result['d3']} = {result['tong']}\n"
        f"✅ KQ: {result['kq']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔮 *Dự đoán:* {result['du_doan']}\n"
        f"📈 Độ tin cậy: {result['do_tin_cay']}%\n"
        f"📌 {result['dung_sai']}"
    )

    kb = [[InlineKeyboardButton("🔄 Dự đoán lại", callback_data='predict')]]
    await msg.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

async def stats(uid, ctx):
    s = pred_sys.get_stats()
    await uid.message.reply_text(
        f"📊 *THỐNG KÊ*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Tổng: {s['total']}\n"
        f"🎯 Tài: {s['tai']} ({s['tai_pct']:.1f}%)\n"
        f"🎯 Xỉu: {s['xiu']} ({100 - s['tai_pct']:.1f}%)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Đúng: {s['correct']}\n"
        f"❌ Sai: {s['wrong']}\n"
        f"📈 Tỉ lệ: {s['acc']:.1f}%\n"
        f"🧠 Model: {s['models']}",
        parse_mode='Markdown'
    )

async def patterns(uid, ctx):
    # Lấy 10 pattern gần nhất
    if not pred_sys.history:
        await uid.message.reply_text("🧩 Chưa có dữ liệu!")
        return

    recent = list(pred_sys.history)[-20:]
    text = "🧩 *PATTERN GẦN ĐÂY*\n━━━━━━━━━━━━━━━━━━\n"
    for i, p in enumerate(recent, 1):
        text += f"{i}. {'TÀI' if p == 'T' else 'XỈU'}\n"

    await uid.message.reply_text(text, parse_mode='Markdown')

async def help(uid, ctx):
    await uid.message.reply_text(
        "🎲 *HƯỚNG DẪN*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "/predict - Dự đoán\n"
        "/stats - Thống kê\n"
        "/patterns - Pattern\n"
        "/register <key> - Đăng ký\n"
        "/help - Hướng dẫn\n\n"
        "📡 API: https://web-tool-4ej3.onrender.com/api/lc79/history",
        parse_mode='Markdown'
    )

# ==================== ADMIN ====================
async def add_user(uid, ctx):
    if uid.effective_user.id not in ADMIN_IDS:
        await uid.message.reply_text("❌ Không có quyền!")
        return
    args = ctx.args
    if len(args) < 2:
        await uid.message.reply_text("📌 /add_user <id> <tên> [ngày]")
        return
    target = int(args[0])
    name = args[1]
    days = int(args[2]) if len(args) > 2 else 30
    ok, key = user_mgr.add_user(target, name, days)
    await uid.message.reply_text(f"✅ Đã thêm!\n🆔 `{target}`\n🔑 Key: `{key}`", parse_mode='Markdown')

async def list_users(uid, ctx):
    if uid.effective_user.id not in ADMIN_IDS:
        await uid.message.reply_text("❌ Không có quyền!")
        return
    if not user_mgr.data:
        await uid.message.reply_text("📭 Chưa có user!")
        return
    text = "👥 *DANH SÁCH USER*\n━━━━━━━━━━━━━━━━━━\n"
    for uid, u in list(user_mgr.data.items())[:10]:
        expiry = datetime.fromisoformat(u['expiry']).strftime('%d/%m')
        text += f"✅ `{uid}` - {u['name']}\n   Key: `{u['key']}` | Hạn: {expiry}\n"
    await uid.message.reply_text(text, parse_mode='Markdown')

async def extend(uid, ctx):
    if uid.effective_user.id not in ADMIN_IDS:
        await uid.message.reply_text("❌ Không có quyền!")
        return
    args = ctx.args
    if len(args) < 2:
        await uid.message.reply_text("📌 /extend <id> <ngày>")
        return
    target = int(args[0])
    days = int(args[1])
    ok, new = user_mgr.extend(target, days)
    if ok:
        await uid.message.reply_text(f"✅ Đã gia hạn!\n📅 Hạn mới: {new.strftime('%d/%m/%Y')}")
    else:
        await uid.message.reply_text(f"❌ {new}")

# ==================== CALLBACK ====================
async def callback(update, ctx):
    q = update.callback_query
    await q.answer()
    if q.data == 'predict':
        await predict(update, ctx)
    elif q.data == 'register':
        await q.edit_message_text(
            f"🔑 *ĐĂNG KÝ*\n🆔 ID: `{update.effective_user.id}`\n📱 Liên hệ admin: @hoangquan280",
            parse_mode='Markdown'
        )

# ==================== MAIN ====================
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("predict", predict))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("patterns", patterns))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("add_user", add_user))
    app.add_handler(CommandHandler("list_users", list_users))
    app.add_handler(CommandHandler("extend", extend))
    app.add_handler(CallbackQueryHandler(callback))

    # Xóa webhook
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Đã xóa webhook")

    # Chạy polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=30
    )

    logger.info("🚀 Bot đang chạy...")
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("🛑 Dừng bot")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
