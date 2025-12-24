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

# گرفتن توکن‌ها از فایل .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")

# --- استفاده از ساختار سایت Agenta برای تنظیم محیط ---
# تنظیم کلید و هاست مستقیماً در متغیرهای محیطی (Environment Variables)
os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY
os.environ["AGENTA_HOST"] = "https://cloud.agenta.ai/api"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

# ================= Agenta Init =================
try:
    # اینیت با تنظیماتی که در os.environ گذاشتیم
    ag.init()
    logger.info("✅ Agenta initialized with specified host.")
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
    await update.message.reply_text(
        "🤖 سلام!\nایده‌ات رو بفرست تا برات پردازش کنم."
    )
    logger.info("/start received")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info("📩 User message received: %s", user_text)

    status_message = await update.message.reply_text("⏳ در حال پردازش...")

    try:
        # 1. دریافت کانفیگ برای پیدا کردن نام متغیر ورودی
        config = ag.ConfigManager.get_from_registry(
            app_slug="Prompt-Writer",
            environment_slug="development"
        )
        
        llm_config = config.get("llm_config", {})
        input_keys = llm_config.get("input_keys", [])
        target_key = input_keys[0] if input_keys else "user_idea"
        
        logger.info(f"🔍 Target Key: {target_key}")

        # 2. اجرای درخواست با استفاده از ag.client.run
        # طبق لاگ‌ها، متد run در ag.client وجود دارد و این روش درست است
        
        logger.info(f"📤 Calling ag.client.run...")

        # اجرا در ترد جداگانه (چون ag.client.run ممکن است همگام باشد)
        result = await asyncio.to_thread(
            ag.client.run,
            app_slug="Prompt-Writer",
            environment_slug="development",
            inputs={target_key: user_text}
        )

        logger.info("✅ Run successful")

        # 3. نمایش نتیجه
        # اگر نتیجه دیکشنری بود، سعی کن متنش را پیدا کن، اگر رشته بود همان را نشان بده
        final_output = str(result)
        if isinstance(result, dict):
            # تلاش برای پیدا کردن متن اصلی در دیکشنری خروجی
            final_output = result.get('data') or result.get('text') or result.get('response') or result.get('message') or str(result)

        await status_message.edit_text(f"🤖 پاسخ:\n\n{final_output}")

    except Exception as e:
        logger.exception("❌ Error in handle_message")
        await status_message.edit_text(
            f"❌ خطا:\n{str(e)}"
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
