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
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

logging.basicConfig(level=logging.INFO)

# ================= AGENTA =================
os.environ["AGENTA_API_KEY"] = os.getenv("AGENTA_API_KEY")

ag.init()

def call_agenta(user_idea: str) -> str:
    logger.info("Sending request to Agenta")
    result = ag.run(
        app_slug="Prompt-Writer",
        environment_slug="development",
        inputs={
            "user_idea": user_idea
        },
    )
    logger.info("Agenta response received")
    return result.get("output", "❌ خروجی‌ای از Agenta دریافت نشد")

# ================= TELEGRAM =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 سلام!\nایده‌ات رو بفرست تا برات پرامپت حرفه‌ای بسازم."
    )
    logger.info("/start received")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info("User message received: %s", update.message.text)
    await update.message.reply_text("⏳ در حال پردازش...")

    try:
        result = ag.run(
            app_slug="Prompt-Writer",
            environment_slug="development",
            inputs={"user_idea": user_text},
        )

        output = result.get("output", "❌ خروجی‌ای دریافت نشد")
        await update.message.reply_text("🧠 نتیجه:\n\n" + output)

    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{e}")

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Telegram bot started (Polling)")
    app.run_polling()
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
