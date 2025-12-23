import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from string import Template
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters, Application
)

import agenta as ag
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("📌 bot.py loaded successfully")

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

logging.basicConfig(level=logging.INFO)

# ================= AGENTA =================
ag.init()

config = ag.ConfigManager.get_from_registry(
    app_slug="Prompt-Writer",
    environment_slug="development",
)

# ================= TELEGRAM =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 سلام!\nایده‌ات رو بفرست تا برات پرامپت حرفه‌ای بسازم."
    )
    logger.info("/start received")
    if not update.message or not update.message.text:
        return
def extract_prompt_text(prompt_template):
    if isinstance(prompt_template, str):
        return prompt_template

    elif isinstance(prompt_template, dict):
        # اولویت با کلیدهای رایج
        for key in ["text", "template", "fa", "en", "body", "content"]:
            value = prompt_template.get(key)
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                # بررسی لایه دوم
                for subkey in ["fa", "en", "text"]:
                    subvalue = value.get(subkey)
                    if isinstance(subvalue, str):
                        return subvalue

    raise ValueError("قالب پرامپت قابل تبدیل به متن نیست.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info("📩 User message received: %s", user_text)

    await update.message.reply_text("⏳ در حال ساخت پرامپت...")

    try:
        # گرفتن کانفیگ از Agenta
        config = ag.ConfigManager.get_from_registry(
            app_slug="Prompt-Writer",
            environment_slug="development",
        )

        logger.info("✅ Agenta config loaded successfully")

        # فرض: داخل Agenta یک فیلد prompt داری
    
        prompt_template = config.get("prompt")
        if not isinstance(prompt_template, str):
            raise ValueError("❌ قالب پرامپت معتبر نیست")
        if not prompt_template:
            raise ValueError("❌ prompt template در Agenta پیدا نشد")

        # جایگذاری ورودی کاربر
        prompt_template = config.get("prompt")
        template_text = extract_prompt_text(prompt_template)
        final_prompt = template_text.replace("{{user_idea}}", user_text)
        logger.info("🧠 Prompt generated successfully")

        await update.message.reply_text(
            "🧠 پرامپت آماده:\n\n" + final_prompt
        )

    except Exception as e:
        logger.exception("❌ Error while generating prompt")
        await update.message.reply_text(
            "❌ خطا در ساخت پرامپت:\n" + str(e)
        )
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)
application.run_polling()
#------------------ ERROR HANDLER ---------------
async def error_handler(update, context):
    logger.exception("Unhandled error", exc_info=context.error) 

# تعریف logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# هندلر HTTP برای بررسی سلامت
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

# سرور سلامت
def start_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# اجرای سرور در ترد جداگانه
threading.Thread(target=start_fake_server, daemon=True).start()

# تابع اصلی
def main():
    logger.info("📌 Entered main()")
    logger.info("🚀 Bot is starting polling...")
    
if __name__ == "__main__":
    main()
