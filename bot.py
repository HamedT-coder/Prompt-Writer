import os
import asyncio
import logging
from telegram import Update
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import agenta as ag
from dotenv import load_dotenv

# ================= تنظیمات =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")

# --- تنظیم دقیقا طبق ساختار سایت Agenta ---
os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY
os.environ["AGENTA_HOST"] = "https://cloud.agenta.ai/api"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

# ================= Agenta Init =================
try:
    ag.init()
    logger.info("✅ Agenta initialized.")
except Exception as e:
    logger.error(f"Agenta init failed: {e}")

# ================= سرور سلامت =================
class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass 

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"🌐 Fake server listening on port {port}")
    server.serve_forever()

# ================= هندلرهای تلگرام =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات آماده است. هر متنی بفرستید کانفیگ را چاپ می‌کنم.")
    logger.info("/start received")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # هر پیامی که کاربر بفرستد، فقط باعث می‌شود کانفیگ لود و چاپ شود
    logger.info("📩 Fetching config...")

    status_message = await update.message.reply_text("⏳ در حال دریافت کانفیگ...")

    try:
        # دریافت کانفیگ طبق ساختار سایت
        config = await asyncio.to_thread(
            ag.ConfigManager.get_from_registry,
            app_slug="Prompt-Writer",
            environment_slug="development"
        )
        
        logger.info("✅ Config received.")

        # تبدیل آبجکت کانفیگ به رشته برای نمایش در تلگرام
        config_text = str(config)

        # محدودیت طول پیام تلگرام (4096 کاراکتر)
        if len(config_text) > 4000:
            config_text = config_text[:4000] + "\n\n... (متن کوتاه شد)"

        await status_message.edit_text(f"📋 کانفیگ دریافتی:\n\n{config_text}")

    except Exception as e:
        logger.exception("❌ Error fetching config")
        await status_message.edit_text(
            f"❌ خطا در دریافت کانفیگ:\n{str(e)}"
        )

def main():
    logger.info("📌 Entered main()")

    threading.Thread(
        target=start_fake_server,
        daemon=True
    ).start()

    logger.info("🌐 Fake server started")

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("🤖 Telegram bot started")
    application.run_polling()

if __name__ == "__main__":
    main()
