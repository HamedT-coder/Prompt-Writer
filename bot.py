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
# اصلاح ایمپورت کلاینت:
# به جای استفاده از ag.Client (که وجود ندارد)، آن را از زیرپوشه client وارد می‌کنیم
from agenta.client import client 
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

# ================= کلاینت Agenta =================
# استفاده از کلاس Client که مستقیماً ایمپورت کردیم
client = Client(api_key=AGENTA_API_KEY)

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
        # 1. دریافت اطلاعات کانفیگ (برای فهمیدن اینکه ورودی برنامه چیست)
        # این فقط اطلاعات ساختاری را می‌خواند، اجرا نمی‌کند
        config = await asyncio.to_thread(
            lambda: ag.ConfigManager.get_from_registry(
                app_slug="Prompt-Writer",
                environment_slug="development",
            )
        )
        logger.info("✅ Agenta config loaded for input detection")

        # 2. پیدا کردن کلیدهای ورودی (Input Keys)
        # مثلا در لاگ قبلی دیدیم که 'country' بود. ممکنه 'user_idea' یا چیز دیگه ای باشه.
        llm_config = config.get("llm_config", {})
        input_keys = llm_config.get("input_keys", [])
        
        # اگر کلیدی مشخص نشده بود، از یک نام پیش‌فرض استفاده می‌کنیم
        target_key = input_keys[0] if input_keys else "user_idea"
        
        logger.info(f"🔍 Detected input key: {target_key}")

        # 3. آماده سازی داده ورودی برای Agenta
        # ما متن تلگرام را به کلید پیدا شده نسبت می‌دهیم
        # مثلا: {"country": "تصویر یک ماشین"}
        payload = {target_key: user_text}

        # 4. اجرای اپلیکیشن روی سرور Agenta
        # نکته: client.run متد همگام (Sync) است، پس باید در ترد جداگانه اجرا شود
        logger.info("📤 Triggering Agenta Run...")
        result = await asyncio.to_thread(
            client.run,
            app_slug="Prompt-Writer",
            environment_slug="development",
            input_data=payload
        )

        logger.info("✅ Agenta Run completed")

        # 5. نمایش نتیجه به کاربر
        # Agenta معمولاً رشته نهایی را برمی‌گرداند، اگر دیکشنری بود، متن آن را می‌گیریم
        final_output = str(result) if not isinstance(result, str) else result

        await status_message.edit_text(f"🤖 پاسخ سیستم:\n\n{final_output}")

    except Exception as e:
        logger.exception("❌ Error in Agenta execution")
        await status_message.edit_text(
            f"❌ خطا در ارتباط با Agenta:\n{str(e)}"
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
