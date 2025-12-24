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

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

# ================= Agenta Init =================
try:
    # این دستور کلاینت سراسری (ag.client) را آماده می‌کند
    ag.init()
    
    # دیباگ: برای اطمینان چک می‌کنیم که کلاینت سراسری وجود دارد
    if hasattr(ag, 'client'):
        logger.info("✅ Agenta Global Client detected successfully.")
    else:
        logger.warning("⚠️ Agenta Global client not found.")
        
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
        # 1. دریافت کانفیگ برای پیدا کردن نام متغیر (input_key)
        config = await asyncio.to_thread(
            ag.ConfigManager.get_from_registry,
            app_slug="Prompt-Writer",
            environment_slug="development"
        )
        
        llm_config = config.get("llm_config", {})
        input_keys = llm_config.get("input_keys", [])
        target_key = input_keys[0] if input_keys else "user_idea"
        
        logger.info(f"🔍 Target Key: {target_key}")

        # 2. اجرای درخواست با استفاده از کلاینت سراسری ag.client
        # این روش احتمالا متد run دارد و آدرس را خودش مدیریت می‌کند
        
        # ساخت پارامترها بر اساس متد معمول
        run_params = {
            "app_slug": "Prompt-Writer",
            "environment_slug": "development",
            "inputs": {
                target_key: user_text
            }
        }

        logger.info(f"📤 Triggering run via ag.client...")

        # اجرا در ترد جداگانه
        result = await asyncio.to_thread(
            ag.client.run, # فراخوانی متد run از کلاینت سراسری
            **run_params
        )

        logger.info("✅ Run executed successfully")

        # 3. نمایش نتیجه
        final_output = str(result)
        
        await status_message.edit_text(f"🤖 پاسخ:\n\n{final_output}")

    except Exception as e:
        logger.exception("❌ Error in run process")
        # اگر خطا مربوط به نام متد بود، به کاربر پیشنهاد دیباگ می‌دهیم
        await status_message.edit_text(
            f"❌ خطا:\n{str(e)}\n\n"
            "(اگر خطا مربوط به متد run بود، لطفا در کنسول لاگ را بفرستید)"
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
