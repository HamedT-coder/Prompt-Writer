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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("🚀 /start command received")

    if not update.message:
        logger.warning("⚠️ /start received but update.message is None")
        return

    await update.message.reply_text(
        "🤖 سلام!\n\n"
        "ایده‌ات رو بفرست تا با استفاده از Agenta برات یک پرامپت حرفه‌ای بسازم.\n\n"
        "✍️ فقط کافیه توضیح کوتاهت رو ارسال کنی."
    )

AGENTA_BASE_URL = "https://cloud.agenta.ai/api"
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info("📩 User message received: %s", user_text)

    status_msg = await update.message.reply_text("⏳ در حال ساخت پرامپت با Agenta...")

    url = (
    "https://cloud.agenta.ai/api/apps/"
    "Prompt-Writer/environments/development/runs"
    )

    headers = {
    "Authorization": f"Bearer {AGENTA_API_KEY}",
    "Content-Type": "application/json",
    }

    payload = {
    "inputs": {
        "user_idea": user_text
        }
    }


    try:
        response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=90
    )


        logger.info("📡 Agenta status code: %s", response.status_code)

        if response.status_code != 200:
            logger.error("❌ Agenta error response: %s", response.text)
            await status_msg.edit_text(
                f"❌ خطا از Agenta\nStatus: {response.status_code}\n{response.text}"
            )
            return

        data = response.json()
        logger.info("✅ Agenta response received")

        # تلاش برای استخراج خروجی
        output = (
            data.get("outputs", {}).get("output")
            or data.get("outputs")
            or str(data)
        )


        await status_msg.edit_text(
            "🧠 پرامپت تولید شده:\n\n" + output
        )

    except requests.exceptions.Timeout:
        logger.exception("⏱ Timeout")
        await status_msg.edit_text("❌ خطا: زمان پاسخ Agenta طولانی شد")

    except Exception as e:
        logger.exception("❌ Unexpected error")
        await status_msg.edit_text(f"❌ خطای غیرمنتظره:\n{str(e)}")

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
