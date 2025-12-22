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

# ================== ENV ==================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")
PORT = int(os.getenv("PORT", 10000))  # Render PORT

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set")
if not AGENTA_API_KEY:
    raise RuntimeError("❌ AGENTA_API_KEY is not set")

# ================== LOG ==================
logging.basicConfig(level=logging.INFO)

# ================== AGENTA ==================
os.environ["AGENTA_API_KEY"] = AGENTA_API_KEY
ag.init()

# ================== FAKE HTTP SERVER ==================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_fake_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logging.info(f"🌐 Fake server running on port {PORT}")
    server.serve_forever()

# ================== TELEGRAM ==================
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
            inputs={"user_idea": user_text},
        )

        output = result.get("output", "❌ خروجی‌ای دریافت نشد")

        await update.message.reply_text("🧠 پرامپت پیشنهادی:\n\n" + output)

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارتباط با Agenta:\n{e}")

# ================== MAIN ==================
def main():
    # 🔹 Start fake server in background
    threading.Thread(target=run_fake_server, daemon=True).start()

    # 🔹 Telegram bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("🤖 Prompt Writer Bot started (Polling + Fake Server)...")
    application.run_polling()

if __name__ == "__main__":
    main()
