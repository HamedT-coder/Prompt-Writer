import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import agenta as ag

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------- ENV ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN تنظیم نشده")

if not AGENTA_API_KEY:
    raise RuntimeError("❌ AGENTA_API_KEY تنظیم نشده")

# ---------------- AGENTA ----------------
os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY

try:
    ag.init()
    logger.info("✅ Agenta initialized")
except Exception as e:
    logger.exception("❌ Agenta init failed")
    raise e


def call_agenta(user_idea: str) -> str:
    logger.info("📨 Sending to Agenta: %s", user_idea)

    try:
        result = ag.run(
            app_slug="Prompt-Writer",
            environment_slug="development",
            inputs={
                "user_idea": user_idea
            },
        )

        logger.info("📩 Agenta raw response: %s", result)

        output = result.get("output")
        if not output:
            return "⚠️ Agenta خروجی‌ای نداد"

        return output

    except Exception as e:
        logger.exception("❌ Agenta error")
        return f"❌ خطا در Agenta:\n{e}"


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("▶️ /start received from %s", update.effective_user.id)
    await update.message.reply_text(
        "🤖 سلام!\nایده‌ات رو بفرست تا برات پرامپت حرفه‌ای بسازم."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info("💬 Message received: %s", user_text)

    await update.message.reply_text("⏳ در حال پردازش...")

    result = call_agenta(user_text)

    await update.message.reply_text(result)
    logger.info("✅ Response sent to user")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("🔥 Telegram error", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ یک خطای داخلی رخ داد. لطفاً دوباره تلاش کن."
        )


# ---------------- MAIN ----------------
def main():
    logger.info("🚀 Starting bot...")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    application.add_error_handler(error_handler)

    logger.info("🤖 Bot running (polling)")
    application.run_polling()


if __name__ == "__main__":
    main()
