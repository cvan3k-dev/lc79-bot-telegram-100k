import asyncio
import logging
import os
import aiohttp
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ──────────────────────────────────────────────
TOKEN = os.getenv('BOT_TOKEN')
API_HISTORY = 'https://web-tool-4ej3.onrender.com/api/lc79/history'

# ── LOGGING ─────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── KIỂM TRA ──────────────────────────────────────────────
if not TOKEN:
    logger.error("❌ KHÔNG TÌM THẤY BOT_TOKEN!")
    sys.exit(1)

logger.info(f"✅ Bot Token: {TOKEN[:10]}...")

# ── LỆNH BOT ──────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 *BOT DỰ ĐOÁN TÀI XỈU*\n\n"
        "/predict - Dự đoán phiên hiện tại\n"
        "/test - Kiểm tra kết nối API",
        parse_mode='Markdown'
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang kiểm tra API...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_HISTORY, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    count = len(data.get('data', []))
                    await update.message.reply_text(f"✅ API hoạt động! {count} phiên")
                else:
                    await update.message.reply_text(f"❌ API lỗi: {response.status}")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang lấy dữ liệu...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_HISTORY, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('data', [])
                    if items:
                        valid = None
                        for item in items:
                            if all(k in item for k in ['d1', 'd2', 'd3', 'phiên', 'kết_quả']):
                                valid = item
                                break
                        
                        if valid:
                            msg = (
                                f"🎲 *PHIÊN #{valid['phiên']}*\n"
                                f"🎯 {valid['d1']}-{valid['d2']}-{valid['d3']}\n"
                                f"📊 Tổng: {valid['tổng']}\n"
                                f"✅ Kết quả: {valid['kết_quả'].upper()}"
                            )
                            await update.message.reply_text(msg, parse_mode='Markdown')
                        else:
                            await update.message.reply_text("❌ Không tìm thấy phiên có kết quả!")
                    else:
                        await update.message.reply_text("❌ API trả về rỗng!")
                else:
                    await update.message.reply_text(f"❌ API trả về: {response.status}")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# ── MAIN ──────────────────────────────────────────────────
async def main():
    logger.info("🚀 Đang khởi động bot...")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("predict", predict))
    
    # Xóa webhook
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Đã xóa webhook")
    
    # Bắt đầu polling
    logger.info("🔄 Bắt đầu polling...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

# ── ENTRY POINT ──────────────────────────────────────────
if __name__ == "__main__":
    # Cách chạy an toàn cho Render
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "already running" in str(e):
            logger.warning("⚠️ Event loop đã chạy, tạo loop mới...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        else:
            raise
