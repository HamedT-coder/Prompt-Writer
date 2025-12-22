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
    filters,
)

import agenta as ag
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

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

# ================= FAKE SERVER =================
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

threading.Thread(target=start_fake_server, daemon=True).start()

def main():
    # ✅ اول پورت رو باز کن (خیلی مهم)
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    print(f"🌐 Fake server listening on {PORT}")

    # 🔹 بعد ربات رو تو thread جدا اجرا کن
    threading.Thread(target=run_bot, daemon=True).start()

    # 🔒 سرور باید بلاک کنه
    server.serve_forever()

if __name__ == "__main__":
    main()
