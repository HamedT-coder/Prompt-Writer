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
from agenta.sdk.types import PromptTemplate
from agenta.client import Client
import agenta as ag
from dotenv import load_dotenv
import requests

# ================= تنظیمات =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")

os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY
os.environ["AGENTA_HOST"] = "https://cloud.agenta.ai/api"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

try:
    ag.init()
    logger.info("✅ Agenta initialized.")
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
Authorization: ApiKey YOUR_API_KEY
``` :contentReference[oaicite:5]{index=5}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("⏳ در حال دریافت پاسخ از Agenta...")

    try:
        url = "https://cloud.agenta.ai/services/completion/run"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"ApiKey {os.getenv('AGENTA_API_KEY')}",
        }
        payload = {
            "environment": "development",
            "app": "Prompt-Writer",
            "inputs": {"user_idea": user_text},
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        data = response.json()
        output = data.get("data") or data.get("output") or str(data)

        await update.message.reply_text(f"🧠 خروجی:\n{output}")

    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{e}")

def main():
    logger.info("📌 Entered main()")
    threading.Thread(target=start_fake_server, daemon=True).start()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 Telegram bot started")
    application.run_polling()

if __name__ == "__main__":
    main()
