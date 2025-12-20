import os
import logging
import asyncio
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

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------- Env Vars ----------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")
AGENTA_HOST = os.getenv("AGENTA_HOST")
PORT = int(os.getenv("PORT", 10000))

if not TELEGRAM_BOT_TOKEN:
    raise EnvironmentError("Missing TELEGRAM_BOT_TOKEN environment variable")
if not AGENTA_API_KEY:
    raise EnvironmentError("Missing AGENTA_API_KEY environment variable")
if not AGENTA_HOST:
    raise EnvironmentError("Missing AGENTA_HOST environment variable")

# ---------------- Agenta Client ----------------
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

# ---------------- FastAPI ----------------
app = FastAPI()

@app.get("/")
async def health():
    return {"status": "ok"}

# ---------------- Telegram Handlers ----------------
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
    if not user_text:
        return
    await update.message.reply_text("⏳ در حال تولید پرامپت...")
    prompt = agenta_client.generate_prompt(user_text)
    await update.message.reply_text(prompt)

# ---------------- Bot Runner ----------------
async def run_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

---------------- Run Bot & Server ----------------

async def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
await application.initialize()
await application.start()
await application.bot.initialize()
await application.updater.start_polling()
await application.updater.idle()
