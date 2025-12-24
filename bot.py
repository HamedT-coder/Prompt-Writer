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

# آدرس صحیح که از لاگ‌های شما استخراج شد
AGENTA_API_URL = "https://cloud.agenta.ai"

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

    status_message = await update.message.reply_text("⏳ در حال پردازش...")

    try:
        # 1. دریافت کانفیگ برای پیدا کردن نام متغیر ورودی
        config = await asyncio.to_thread(
            ag.ConfigManager.get_from_registry,
            app_slug="Prompt-Writer",
            environment_slug="development"
        )
        
        llm_config = config.get("llm_config", {})
        input_keys = llm_config.get("input_keys", [])
        target_key = input_keys[0] if input_keys else "user_idea"
        
        logger.info(f"🔍 Target Key: {target_key}")

        # 2. ارسال درخواست مستقیم به API با آدرس درست
        # ساخت آدرس کامل برای اجرا
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

        logger.info(f"📤 Sending POST to: {endpoint}")

        # ارسال درخواست
        response = await asyncio.to_thread(
            requests.post,
            endpoint,
            headers=headers,
            json=payload
        )

        # بررسی وضعیت
        if response.status_code != 200:
            logger.error(f"Agenta Error {response.status_code}: {response.text}")
            raise ValueError(f"خطا از سرور Agenta: {response.status_code}")

        # دریافت نتیجه
        result_data = response.json()
        
        # استخراج متن نهایی. ساختار معمولا 'data' یا 'output' است
        final_output = result_data.get('data') or result_data.get('output') or result_data.get('result') or str(result_data)

        logger.info("✅ Success")

        await status_message.edit_text(f"🤖 پاسخ سیستم:\n\n{final_output}")

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
