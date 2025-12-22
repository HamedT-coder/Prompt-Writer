import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import agenta as ag
from dotenv import load_dotenv

# ---------- Load env ----------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set")
if not AGENTA_API_KEY:
    raise RuntimeError("❌ AGENTA_API_KEY is not set")

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------- Agenta Init ----------
os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY
ag.init()

# ---------- Telegram Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 سلام!\n"
        "ایده‌ات رو بفرست تا برات یک پرامپت حرفه‌ای انگلیسی بسازم ✨"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    await update.message.reply_text("⏳ در حال ساخت پرامپت...")

    try:
        result = ag.run(
            app_slug="Prompt-Writer",
            environment_slug="development",
            inputs={
                "user_idea": user_text
            }
        )

        prompt = result.get("output", "❌ خروجی‌ای دریافت نشد")

        await update.message.reply_text(
            "🧠 پرامپت پیشنهادی:\n\n" + prompt
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در ارتباط با Agenta:\n{str(e)}"
        )

# ---------- Main ----------
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Prompt Writer Bot started (Polling)...")
    application.run_polling()

if __name__ == "__main__":
    main()
