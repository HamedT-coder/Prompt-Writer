import os
import asyncio
import logging
import requests
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

# اصلاح مهم: پیش‌فرض را به api.agenta.ai تغییر دادیم
AGENTA_API_URL = os.getenv("AGENTA_API_URL", "https://api.agenta.ai")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

try:
    ag.init()
    logger.info("Agenta initialized.")
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

    status_message = await update.message.reply_text("⏳ در حال پردازش با Agenta...")

    try:
        # 1. دریافت کانفیگ (برای پیدا کردن کلید ورودی)
        # اگر در لاگ قبلی دیدیم environment_slug = development بود، اینجا development می‌گذاریم
        config = await asyncio.to_thread(
            ag.ConfigManager.get_from_registry,
            app_slug="Prompt-Writer",
            environment_slug="development",
            # variant_slug="default"  # اگر development نداشتید این را فعال کنید
        )
        
        logger.info("✅ Agenta config loaded")

        # پیدا کردن کلید ورودی
        llm_config = config.get("llm_config", {})
        input_keys = llm_config.get("input_keys", [])
        target_key = input_keys[0] if input_keys else "user_idea"
        
        logger.info(f"🔍 Detected input key: {target_key}")

        # 2. ارسال درخواست Run به API Agenta
        # آدرس را با api.agenta.ai می‌سازیم
        endpoint = f"{AGENTA_API_URL}/api/v1/applications/Prompt-Writer/environments/development/run"
        
        headers = {
            "Authorization": f"Bearer {AGENTA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": {
                target_key: user_text
            }
        }

        logger.info(f"📤 POST Request to: {endpoint}")

        # استفاده از requests در ترد جداگانه
        response = await asyncio.to_thread(
            requests.post,
            endpoint,
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"Agenta API Error {response.status_code}: {error_text}")
            raise ValueError(f"Agenta Error {response.status_code}: {error_text}")

        result_data = response.json()
        
        # استخراج متن خروجی
        final_output = result_data.get('data') or result_data.get('result') or str(result_data)

        logger.info("✅ Agenta response received")

        await status_message.edit_text(f"🤖 پاسخ سیستم:\n\n{final_output}")

    except Exception as e:
        logger.exception("❌ Error in process")
        await status_message.edit_text(
            f"❌ خطا در ارتباط:\n{str(e)}"
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
