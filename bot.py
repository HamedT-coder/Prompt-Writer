import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")


# ---------- Dummy Web Server ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def start_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


# ---------- Telegram Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✍️ سلام!\n"
        "من ربات Prompt Writer هستم.\n"
        "ایده‌تو بفرست تا پرامپت بسازم."
    )

async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    prompt = (
        "You are an expert prompt engineer.\n"
        f"Create a professional AI prompt for this idea:\n{text}"
    )

    await update.message.reply_text(
        f"🧠 پرامپت:\n```{prompt}```",
        parse_mode="Markdown"
    )


def main():
    # Start fake web server
    threading.Thread(target=start_web_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt))

    print("🤖 Bot running with polling + web port")
    app.run_polling()


if __name__ == "__main__":
    main()
