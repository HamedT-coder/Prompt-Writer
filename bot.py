import os
import asyncio
import logging
from typing import Optional

import requests
from fastapi import FastAPI
import uvicorn

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ======================================================
# Logging
# ======================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("prompt-bot")

# ======================================================
# Environment Variables
# ======================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")
AGENTA_HOST = os.getenv("AGENTA_HOST", "https://cloud.agenta.ai")
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

if not AGENTA_API_KEY:
    raise RuntimeError("Missing AGENTA_API_KEY")

# ======================================================
# Agenta Client
# ======================================================
class AgentaClient:
    def __init__(self, host: str, api_key: str, timeout: int = 30):
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def generate_prompt(self, user_text: str) -> str:
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

            result = (
                data.get("outputs", {})
                .get("response")
            )

            if not result:
                return "❌ پاسخی از Agenta دریافت نشد."

            return result.strip()

        except requests.exceptions.Timeout:
            return "⏳ پاسخ Agenta طول کشید، دوباره امتحان کن."
        except requests.exceptions.RequestException as exc:
            logger.error("Agenta error: %s", exc)
            return "❌ خطا در ارتباط با Agenta."


agenta = AgentaClient(
    host=AGENTA_HOST,
    api_key=AGENTA_API_KEY,
)

# ======================================================
# Telegram Bot Handlers
# ======================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام!\n\n"
        "من دستیار فارسی نوشتن پرامپت هستم ✨\n"
        "ایده یا درخواستت رو بفرست تا برات یک پرامپت حرفه‌ای بسازم."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 راهنما:\n\n"
        "هر چیزی که می‌خوای از هوش مصنوعی بگیری رو به زبان ساده بنویس.\n"
        "من اون رو تبدیل به یک پرامپت استاندارد می‌کنم.\n\n"
        "مثال:\n"
        "«یه پرامپت برای تولید کپشن اینستاگرام درباره استارتاپ‌ها»"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: Optional[str] = update.message.text

    if not text or len(text.strip()) < 5:
        await update.message.reply_text("❗ لطفاً توضیح کامل‌تری بنویس.")
        return

    await update.message.reply_text("⏳ در حال ساخت پرامپت...")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, agenta.generate_prompt, text
    )

    await update.message.reply_text(
        f"📝 پرامپت پیشنهادی:\n\n{result}"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram error: %s", context.error)

# ======================================================
# FastAPI (for Render Free)
# ======================================================
app = FastAPI()


@app.get("/")
async def health():
    return {"status": "ok", "bot": "running"}

# ======================================================
# Runners
# ======================================================
async def run_telegram_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)

    await application.initialize()
    await application.start()
    await application.bot.initialize()
    await application.updater.start_polling()
    await application.updater.idle()


async def run_web_server():
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    await asyncio.gather(
        run_telegram_bot(),
        run_web_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())
