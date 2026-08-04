import os
import asyncio
import threading
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import requests

# Import prediction system
from prediction_system import UltraDicePredictionSystem

# ===== CẤU HÌNH =====
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_KEY = os.getenv('ADMIN_KEY')
API_URL = os.getenv('API_URL')
PORT = int(os.getenv('PORT', 10000))

if not BOT_TOKEN or not ADMIN_KEY or not API_URL:
    print('❌ Thiếu biến môi trường!')
    exit(1)

print('✅ Cấu hình OK')

# ===== KHỞI TẠO FLASK =====
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'bot': 'running',
        'time': str(datetime.now())
    })

@app.route('/health')
def health():
    return 'OK'

# ===== KHỞI TẠO PREDICTION SYSTEM =====
prediction_system = UltraDicePredictionSystem()
session_history = []
last_prediction = {'prediction': 'Chưa có', 'confidence': '0%', 'reasons': ['Đang cập nhật...']}
is_updating = False

# ===== HÀM LẤY DỮ LIỆU =====
def fetch_and_update():
    global session_history, last_prediction, is_updating
    
    if is_updating:
        return last_prediction
    
    is_updating = True
    try:
        print('🔄 Đang lấy dữ liệu từ API...')
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        
        if not data.get('list') or len(data['list']) == 0:
            print('⚠️ Không có dữ liệu từ API')
            is_updating = False
            return None
        
        latest_sessions = data['list'][:50]
        print(f'✅ Lấy được {len(latest_sessions)} phiên')
        
        # Reset và cập nhật history
        prediction_system.history = []
        for item in reversed(latest_sessions):
            result = 'T' if item['resultTruyenThong'] == 'TAI' else 'X'
            prediction_system.add_result(result)
        
        # Dự đoán
        pred = prediction_system.get_final_prediction()
        prediction_str = 'Tài' if pred['prediction'] == 'T' else 'Xỉu'
        last_prediction = {
            'prediction': prediction_str,
            'confidence': f"{round(pred['confidence'] * 100)}%",
            'reasons': pred['reasons'] or ['Không có lý do']
        }
        
        # Xây dựng lịch sử
        new_history = []
        for i, item in enumerate(latest_sessions):
            actual = 'Tài' if item['resultTruyenThong'] == 'TAI' else 'Xỉu'
            
            # Tạo hệ thống tạm để dự đoán từng phiên
            temp_system = UltraDicePredictionSystem()
            for j in range(i):
                prev_result = 'T' if latest_sessions[j]['resultTruyenThong'] == 'TAI' else 'X'
                temp_system.add_result(prev_result)
            
            temp_pred = temp_system.get_final_prediction()
            predicted = 'Tài' if temp_pred['prediction'] == 'T' else 'Xỉu'
            correct = '✅' if predicted == actual else '❌'
            
            new_history.append({
                'id': item.get('id') or item.get('_id') or i,
                'dice': item.get('dices', []),
                'point': item.get('point', 0),
                'actual': actual,
                'predicted': predicted,
                'correct': correct
            })
        
        session_history = new_history[:50]
        print(f'✅ Đã cập nhật {len(session_history)} phiên')
        print(f'🎯 Dự đoán: {last_prediction["prediction"]} ({last_prediction["confidence"]})')
        
        is_updating = False
        return last_prediction
        
    except Exception as e:
        print(f'❌ Lỗi fetch API: {str(e)}')
        is_updating = False
        return None

# ===== TELEGRAM BOT HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🎲 SUNWIN AI PREDICTION BOT

📌 LỆNH:
/du_doan - Xem dự đoán hiện tại
/lich_su - Xem 20 phiên gần nhất
/thong_ke - Thống kê tổng quan
/admin [key] - Đăng nhập admin
/help - Hướng dẫn

🔑 Admin Key: admin123"""
    await update.message.reply_text(text)

async def du_doan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = fetch_and_update()
    if not result:
        await update.message.reply_text('❌ Không thể lấy dữ liệu. Thử lại sau.')
        return
    
    text = f"""🎯 DU DOAN PHIEN TIEP THEO

📊 Du doan: {result['prediction']}
🎯 Do tin cay: {result['confidence']}
📝 Ly do:
"""
    for reason in result['reasons']:
        text += f"- {reason}\n"
    
    await update.message.reply_text(text)

async def lich_su(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not session_history:
        fetch_and_update()
    
    if not session_history:
        await update.message.reply_text('📭 Chưa có dữ liệu. Vui lòng chờ cập nhật.')
        return
    
    text = '📜 LICH SU 20 PHIEN GAN NHAT\n\n'
    for i, item in enumerate(session_history[:20]):
        dice_str = '-'.join(map(str, item['dice']))
        text += f"{i+1}. 🎲 {dice_str} | Diem: {item['point']} | KQ: {item['actual']} | DD: {item['predicted']} {item['correct']}\n"
    
    await update.message.reply_text(text)

async def thong_ke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not session_history:
        fetch_and_update()
    
    total = len(session_history)
    if total == 0:
        await update.message.reply_text('📭 Chưa có dữ liệu thống kê.')
        return
    
    tai = sum(1 for s in session_history if s['actual'] == 'Tài')
    xiu = sum(1 for s in session_history if s['actual'] == 'Xỉu')
    dung = sum(1 for s in session_history if s['correct'] == '✅')
    sai = sum(1 for s in session_history if s['correct'] == '❌')
    
    volatility = prediction_system.session_stats['volatility'] * 100
    entropy = prediction_system.session_stats['entropy']
    
    text = f"""📊 THONG KE TONG QUAN

📌 Tong phien: {total}
🟢 Tai: {tai} ({tai/total*100:.1f}%)
🔴 Xiu: {xiu} ({xiu/total*100:.1f}%)

🎯 Du doan dung: {dung}
❌ Du doan sai: {sai}
📈 Ty le chinh xac: {dung/total*100:.1f}%

📊 Bien dong: {volatility:.1f}%
🧠 Entropy: {entropy:.2f}"""
    
    await update.message.reply_text(text)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('⚠️ Vui lòng nhập key: /admin [key]')
        return
    
    key = context.args[0]
    if key == ADMIN_KEY:
        await update.message.reply_text('✅ Dang nhap admin thanh cong!\nBan co the dung lenh /reset de reset he thong.')
    else:
        await update.message.reply_text('❌ Key khong hop le.')

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('⚠️ Vui long nhap key admin: /admin [key] truoc khi reset.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📖 HUONG DAN SU DUNG

🔹 /start - Bat dau
🔹 /du_doan - Xem du doan
🔹 /lich_su - Xem lich su 20 phien
🔹 /thong_ke - Xem thong ke
🔹 /admin [key] - Dang nhap admin
🔹 /reset - Reset he thong (admin)
🔹 /help - Huong dan

🔑 Admin Key: admin123"""
    await update.message.reply_text(text)

# ===== KHỞI CHẠY BOT =====
def run_bot():
    # Tạo application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Thêm handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('du_doan', du_doan))
    application.add_handler(CommandHandler('lich_su', lich_su))
    application.add_handler(CommandHandler('thong_ke', thong_ke))
    application.add_handler(CommandHandler('admin', admin))
    application.add_handler(CommandHandler('reset', reset))
    application.add_handler(CommandHandler('help', help_command))
    
    # Cập nhật lần đầu
    fetch_and_update()
    
    # Start bot
    print('🚀 Bot đang chạy...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ===== CHẠY FLASK + BOT =====
if __name__ == '__main__':
    # Chạy Flask trong thread riêng
    def run_flask():
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print(f'🌐 HTTP Server chạy trên cổng {PORT}')
    
    # Chạy bot (blocking)
    run_bot()
