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
import re # ایمپورت عبارات باقاعده برای جایگزینی هوشمند
import agenta as ag
from dotenv import load_dotenv

# ================= تنظیمات لاگر =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AGENTA_API_KEY = os.getenv("AGENTA_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not AGENTA_API_KEY:
    raise RuntimeError("AGENTA_API_KEY not set")

# ================= AGENTA =================
# فقط اینیت می‌کنیم، کانفیگ را الان نمی‌گیریم تا برنامه فریز نشود
try:
    ag.init()
    logger.info("Agenta initialized.")
except Exception as e:
    logger.error(f"Agenta init failed: {e}")

#------------------ ERROR HANDLER ---------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled error", exc_info=context.error)

# ================= سرور سلامت (برای Render/Heroku) =================
class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # جلوگیری از لاگ‌های مزاحم HTTP

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"🌐 Fake server listening on port {port}")
    server.serve_forever()

# ------------------ UPDATED EXTRACT FUNCTION ---------------
def extract_prompt_text(prompt_template):
    # اگر داده رشته ساده باشد
    if isinstance(prompt_template, str):
        return prompt_template

    # اگر داده دیکشنری باشد (حالت جدید Agenta)
    if isinstance(prompt_template, dict):
        # حالت 1: ساختار پیام‌های چت (ChatML)
        if 'messages' in prompt_template:
            parts = []
            for msg in prompt_template['messages']:
                if isinstance(msg, dict) and 'content' in msg:
                    # اضافه کردن نقش (System/User) برای خوانایی بهتر
                    role = msg.get('role', 'unknown').capitalize()
                    content = msg['content']
                    parts.append(f"[{role}]: {content}")
            return "\n\n".join(parts)
        
        # حالت 2: جستجوی کلیدهای متنی عادی
        for key in ["text", "template", "fa", "en", "body", "content", "prompt"]:
            value = prompt_template.get(key)
            if isinstance(value, str):
                return value

    raise ValueError(f"قالب پرامپت قابل تبدیل به متن نیست. ساختار: {prompt_template}")

# ================= TELEGRAM HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 سلام!\nایده‌ات رو بفرست تا برات پرامپت حرفه‌ای بسازم."
    )
    logger.info("/start received")

# ------------------ UPDATED HANDLER ---------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info("📩 User message received: %s", user_text)

    status_message = await update.message.reply_text("⏳ در حال ساخت پرامپت...")

    try:
        # دریافت کانفیگ در ترد جداگانه
        config = await asyncio.to_thread(
            lambda: ag.ConfigManager.get_from_registry(
                app_slug="Prompt-Writer",
                environment_slug="development",
            )
        )
        logger.info("✅ Agenta config loaded")

        # دریافت تمپلیت
        prompt_template = config.get("prompt")
        if not prompt_template:
            raise ValueError("❌ کلید 'prompt' در Agenta پیدا نشد")

        # تبدیل به متن
        template_text = extract_prompt_text(prompt_template)

        # جایگزینی هوشمند با Regex:
        # این خط هر چیزی که داخل {{ }} باشد را با متن کاربر جایگزین می‌کند.
        # بنابراین فرقی نمی‌کند نام متغیر شما {{country}} باشد یا {{user_idea}}
        final_prompt = re.sub(r'\{\{.*?\}\}', user_text, template_text)

        logger.info("🧠 Final prompt generated")

        await status_message.edit_text(
            "🧠 پرامپت آماده:\n\n" + final_prompt
        )

    except Exception as e:
        logger.exception("❌ Error while generating prompt")
        await status_message.edit_text(
            "❌ خطا در ساخت پرامپت:\n" + str(e)
        )

# ================= MAIN =================
def main():
    logger.info("📌 Entered main()")

    # 🔹 Fake server در Thread (برای زنده نگه داشتن اپلیکیشن)
    threading.Thread(
        target=start_fake_server,
        daemon=True
    ).start()

    logger.info("🌐 Fake server started")

    # 🔹 ساخت اپلیکیشن تلگرام
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)

    # 🔹 اجرای ربات
    logger.info("🤖 Telegram bot started (Polling)")
    application.run_polling()

if __name__ == "__main__":
    main()
