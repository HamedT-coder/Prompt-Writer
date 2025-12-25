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

# تنظیم محیط Agenta
os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY
os.environ["AGENTA_HOST"] = "https://cloud.agenta.ai/api"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

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
    await update.message.reply_text("ربات آماده است.")
    logger.info("/start received")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    status_message = await update.message.reply_text("⏳ در حال پردازش...")
    logger.info("📩 User message received: %s", user_text)

    try:
        # 1. دریافت کانفیگ (که درست کار می‌کند)
        config = await asyncio.to_thread(
            ag.ConfigManager.get_from_registry,
            app_slug="Prompt-Writer",
            environment_slug="development"
        )
        
        # 2. استخراج اطلاعات از کانفیگ
        llm_config = config.get("llm_config", {})
        input_keys = llm_config.get("input_keys", [])
        target_key = input_keys[0] if input_keys else "user_idea"
        
        logger.info(f"🔍 Found Input Key: {target_key}")
        logger.info(f"🔍 User Text: {user_text}")

        # 3. اجرای درخواست (Run)
        # طبق استانداردهای Agenta، آدرس اجرا به این صورت است
        run_url = f"https://cloud.agenta.ai/api/v1/applications/Prompt-Writer/environments/development/run"
        
        headers = {
            "Authorization": f"Bearer {AGENTA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": {target_key: user_text}
        }

        logger.info(f"📤 Sending POST to: {run_url}")
        logger.info(f"📤 Payload: {payload}")

        response = await asyncio.to_thread(
            requests.post,
            run_url,
            headers=headers,
            json=payload
        )

        # 4. مدیریت پاسخ
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"Agenta Error {response.status_code}: {error_text}")
            
            # اگر خطای دسترسی بود
            if "Unauthorized" in error_text or "401" in str(response.status_code):
                raise ValueError("خطا 401: کلید API شما دسترسی اجرا (Write) را ندارد یا اشتباه است.")
            else:
                raise ValueError(f"خطای سرور: {response.status_code}")

        # موفقیت آمیز بود
        result_data = response.json()
        
        # استخراج متن نهایی
        # معمولا خروجی در کدی به نام data, output یا text است
        final_output = result_data.get('data') or result_data.get('output') or result_data.get('text') or str(result_data)

        logger.info("✅ Run Successful")
        
        await status_message.edit_text(f"🤖 پاسخ هوش مصنوعی:\n\n{final_output}")

    except Exception as e:
        logger.exception("❌ Error")
        await status_message.edit_text(
            f"❌ خطا:\n{str(e)}"
        )

def main():
    logger.info("📌 Entered main()")
    threading.Thread(target=start_fake_server, daemon=True).start()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 Telegram bot started")
    application.run_polling()

if __name__ == "__main__":
    main()
