import os
import threading
import requests
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

# ---------- ENV ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv["AGENTA_API_KEY"]
AGENTA_HOST = os.getenv["AGENTA_HOST"]
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not AGENTA_API_KEY or not AGENTA_HOST:
    raise RuntimeError("AGENTA_HOST or AGENTA_API_KEY is not set")

# ---------- Dummy Web Server (Render) ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def start_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()

# ---------- Agenta Call ----------
# ---------- Agenta Call (with agenta.ConfigManager) ----------
import os
import requests
import agenta as ag

# تنظیم کلید API و میزبان Agenta
os.environ["AGENTA_API_KEY"] = "AGENTA_API_KEY"  # 🔐 کلید واقعی را اینجا قرار بده
os.environ["AGENTA_HOST"] = "https://cloud.agenta.ai/api"

# مقداردهی اولیه Agenta و دریافت پیکربندی
ag.init()
config = ag.ConfigManager.get_from_registry(
    app_slug="Prompt-Writer",
    environment_slug="development"
)

print("✅ پیکربندی دریافت شد:", config)

def call_agenta(user_idea: str) -> str:
    url = f"{config.host}/api/chat"  # استفاده از host از config

    headers = {
        "Authorization": f"Bearer {config.api_key}",  # استفاده از api_key از config
        "Content-Type": "application/json",
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert prompt engineer. "
                    "Your task is to write a high-quality, detailed, and professional AI prompt."
                ),
            },
            {
                "role": "user",
                "content": user_idea,
            },
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # 🟢 اگر ساختار پاسخ متفاوت بود، این قسمت را تنظیم کن
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ خطا در ارتباط با Agenta:\n{str(e)}"
        
# ---------- Telegram Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✍️ سلام!\n"
        "ایده یا توضیح کارت رو بفرست تا با Agenta برات پرامپت حرفه‌ای بسازم."
    )

async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if len(user_text) < 5:
        await update.message.reply_text("❗️ لطفاً توضیح کامل‌تری بفرست.")
        return

    await update.message.reply_text("⏳ در حال ساخت پرامپت...")

    result = call_agenta(user_text)

    await update.message.reply_text(
        f"🧠 پرامپت نهایی:\n\n```{result}```",
        parse_mode="Markdown"
    )

# ---------- Main ----------
def main():
    # Start dummy web server
    threading.Thread(target=start_web_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt)
    )

    print("🤖 Prompt Writer Bot running (Polling + Agenta)")
    app.run_polling()

if __name__ == "__main__":
    main()
