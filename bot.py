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

# --- استفاده از ساختار سایت Agenta (طبق درخواست شما) ---
os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY
# طبق لاگ‌ها، هاست اصلی cloud.agenta.ai است و خود SDK /api را اضافه می‌کند
os.environ["AGENTA_HOST"] = "https://cloud.agenta.ai"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

# ================= Agenta Init =================
try:
    ag.init()
    logger.info("✅ Agenta initialized (Host: %s)", os.environ.get("AGENTA_HOST"))
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

        # 2. تلاش برای اجرا با SDK (ag.client.apps.run)
        result = None
        try:
            logger.info("📤 Attempting SDK Run (ag.client.apps.run)...")
            
            # فرض بر این است که متد run در زیرمجموعه apps قرار دارد
            result = await asyncio.to_thread(
                ag.client.apps.run,
                app_slug="Prompt-Writer",
                environment_slug="development",
                inputs={target_key: user_text}
            )
            logger.info("✅ SDK Run Successful")

        except (AttributeError, TypeError) as sdk_err:
            logger.warning(f"⚠️ SDK Method not found or failed: {sdk_err}")
            logger.info("📤 Fallback to HTTP Request...")

            # 3. روش پشتیبان: درخواست مستقیم HTTP (اگر SDK کار نکرد)
            # با توجه به لاگ‌های شما، آدرس باید شامل /api باشد
            # در حالت فال‌بک، ما آدرس کامل را دستی می‌سازیم
            endpoint = f"https://cloud.agenta.ai/api/v1/applications/Prompt-Writer/environments/development/run"
            
            headers = {
                "Authorization": f"Bearer {AGENTA_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": {target_key: user_text}
            }

            response = await asyncio.to_thread(
                requests.post,
                endpoint,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                raise ValueError(f"HTTP Error {response.status_code}: {response.text}")
            
            result_data = response.json()
            result = result_data.get('data') or result_data.get('text') or str(result_data)

        # 4. نمایش نتیجه
        final_output = str(result)
        if isinstance(result, dict):
            final_output = result.get('data') or result.get('output') or result.get('text') or str(result)

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
