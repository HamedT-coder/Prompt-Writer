import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters, Application
)

from agenta import run_app
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
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

logging.basicConfig(level=logging.INFO)

# ================= AGENTA =================
import agenta as ag

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

        if not prompt_template:
            raise ValueError("❌ prompt template در Agenta پیدا نشد")

        # جایگذاری ورودی کاربر
        final_prompt = prompt_template.replace(
            "{{user_idea}}",
            user_text
        )

        logger.info("🧠 Prompt generated successfully")

        await update.message.reply_text(
            "🧠 پرامپت آماده:\n\n" + final_prompt
        )

    except Exception as e:
        logger.exception("❌ Error while generating prompt")
        await update.message.reply_text(
            "❌ خطا در ساخت پرامپت:\n" + str(e)
        )


def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Telegram bot started (Polling)")
    application.run_polling()
#------------------ ERROR HANDLER ---------------
async def error_handler(update, context):
    logger.exception("Unhandled error", exc_info=context.error) 
    
def main():
    logger.info("📌 Entered main()")
    logger.info("🚀 Bot is starting polling...")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
