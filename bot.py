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
# ایمپورت طبق درخواست شما
from agenta.sdk.types import PromptTemplate
import agenta as ag
from dotenv import load_dotenv

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
    await update.message.reply_text("ربات آماده است. ورودی خود را بفرستید.")
    logger.info("/start received")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("⏳ در حال تولید پرامپت با هوش مصنوعی...")

    try:
        result = await asyncio.to_thread(
            ag.run,
            app_slug="Prompt-Writer",
            environment_slug="development",
            inputs={
                "user_idea": user_text  # ⚠️ دقیقاً باید با input_keys یکی باشد
            }
        )

        output = result.get("output")
        if not output:
            raise ValueError("خروجی‌ای از Agenta دریافت نشد")

        await update.message.reply_text(
            "🧠 پرامپت نهایی:\n\n" + output
        )

    except Exception as e:
        logger.exception("Agenta run failed")
        await update.message.reply_text(f"❌ خطا:\n{e}")

    except Exception as e:
        logger.exception("❌ Error")
        # اگر ایمپورت PromptTemplate کار نکرد، به ما بگو
        if "PromptTemplate" in str(e) or "No module named" in str(e):
            await status_message.edit_text("❌ خطا: کلاس PromptTemplate در این نسخه از Agenta SDK پیدا نشد.")
        else:
            await status_message.edit_text(f"❌ خطا:\n{str(e)}")

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
