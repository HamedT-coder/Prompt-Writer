import os
import asyncio
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# ----------------- Handlers -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✍️ سلام!\n"
        "من ربات Prompt Writer هستم.\n"
        "موضوع یا ایده‌ت رو بفرست تا برات پرامپت بسازم."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 راهنما:\n"
        "- فقط کافیه ایده یا موضوعت رو بفرستی\n"
        "- من برات یک پرامپت حرفه‌ای می‌نویسم"
    )

async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if len(user_text) < 5:
        await update.message.reply_text("❗️ لطفاً یک توضیح کامل‌تر بفرست.")
        return

    # --- نمونه ساده Prompt Writer (قابل توسعه) ---
    prompt = (
        "You are an expert prompt engineer.\n"
        f"Write a high-quality AI prompt based on the following idea:\n\n"
        f"{user_text}\n\n"
        "The prompt should be clear, detailed, and professional."
    )

    await update.message.reply_text(
        "🧠 پرامپت پیشنهادی:\n\n"
        f"```{prompt}```",
        parse_mode="Markdown"
    )

# ----------------- Main -----------------

async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt)
    )

    print("🤖 Prompt Writer Bot started (Polling)...")

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
