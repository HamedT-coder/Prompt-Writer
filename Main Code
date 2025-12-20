"""
Persian Telegram Bot – Prompt Assistant using Agenta (Open-Source)
=================================================================

Requirements:
- Python 3.10+
- python-telegram-bot >= 20
- agenta (self-hosted or cloud, open-source)

Environment Variables:
- TELEGRAM_BOT_TOKEN : Telegram bot token
- AGENTA_API_KEY     : Agenta API key
- AGENTA_HOST        : Agenta host URL (e.g. http://localhost:3000)

Install dependencies:
pip install python-telegram-bot agenta requests python-dotenv
"""

import os
import logging
import asyncio
from typing import Optional

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------
# Configuration & Logging
# ---------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")
AGENTA_HOST = os.getenv("AGENTA_HOST")

if not TELEGRAM_BOT_TOKEN:
    raise EnvironmentError("Missing TELEGRAM_BOT_TOKEN environment variable")

if not AGENTA_API_KEY:
    raise EnvironmentError("Missing AGENTA_API_KEY environment variable")

if not AGENTA_HOST:
    raise EnvironmentError("Missing AGENTA_HOST environment variable")

# ---------------------------------------------------------------------
# Agenta Client
# ---------------------------------------------------------------------


class AgentaClient:
    """Minimal Agenta HTTP client with error handling"""

    def __init__(self, host: str, api_key: str, timeout: int = 30):
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def generate_prompt(self, user_text: str) -> str:
        """
        Calls Agenta app to improve or generate a prompt in Persian
        """
        url = f"{self.host}/api/variants/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": {
                "user_request": user_text,
                "language": "fa",
                "role": "prompt_engineer",
            }
        }

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Agenta standard output handling
            return (
                data.get("outputs", {})
                .get("response", "")
                .strip()
                or "❌ پاسخی از Agenta دریافت نشد."
            )

        except requests.exceptions.RequestException as exc:
            logger.error("Agenta API error: %s", exc)
            return "❌ خطا در ارتباط با سرویس Agenta. لطفاً بعداً تلاش کنید."


agenta_client = AgentaClient(
    host=AGENTA_HOST,
    api_key=AGENTA_API_KEY,
)

# ---------------------------------------------------------------------
# Telegram Handlers
# ---------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 سلام!\n\n"
        "من دستیار فارسیِ نوشتن پرامپت هستم.\n"
        "ایده یا درخواستت رو بفرست تا برات یک پرامپت حرفه‌ای بسازم ✨"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧠 راهنما:\n\n"
        "- فقط کافیه توضیح بدی چی می‌خوای\n"
        "- من اون رو به یک پرامپت استاندارد و بهینه تبدیل می‌کنم\n\n"
        "مثال:\n"
        "«یه پرامپت برای تولید پست اینستاگرام درباره هوش مصنوعی»"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text: Optional[str] = update.message.text

    if not user_text or len(user_text.strip()) < 5:
        await update.message.reply_text("❗ لطفاً توضیح کامل‌تری وارد کن.")
        return

    await update.message.reply_text("⏳ در حال ساخت پرامپت...")

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None, agenta_client.generate_prompt, user_text
    )

    await update.message.reply_text(f"📝 پرامپت پیشنهادی:\n\n{response}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Telegram error: %s", context.error)


# ---------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------


def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("Telegram bot started successfully")
    application.run_polling()


if __name__ == "__main__":
    main()
