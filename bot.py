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

def extract_prompt_text(prompt_template):
    # --- بخش دیباگ (برای فهمیدن مشکل) ---
    logger.info(f"DEBUG - نوع داده دریافتی: {type(prompt_template)}")
    logger.info(f"DEBUG - محتوا: {prompt_template}")
    # ----------------------------------------

    # اگر رشته ساده بود، همان را برگردان
    if isinstance(prompt_template, str):
        return prompt_template

    # اگر دیکشنری بود
    if isinstance(prompt_template, dict):
        # اولویت با کلیدهای مشخص
        priority_keys = ["text", "template", "fa", "en", "body", "content", "prompt", "system", "user"]
        for key in priority_keys:
            value = prompt_template.get(key)
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                # بررسی لایه دوم
                for subkey in ["fa", "en", "text", "content"]:
                    subvalue = value.get(subkey)
                    if isinstance(subvalue, str):
                        return subvalue

        # اگر کلیدهای بالا پیدا نشد، **تمام مقادیر** را نگاه کن
        logger.warning("🔍 کلیدهای استاندارد پیدا نشد، جستجوی کلی...")
        for key, value in prompt_template.items():
            if isinstance(value, str) and len(value) > 10: # فرض بر این است که متن طولانی‌تر از ۱۰ کاراکتر است
                logger.info(f"✅ متن کلید '{key}' انتخاب شد.")
                return value

    # اگر لیست بود (مثلاً مکالمه چت)
    if isinstance(prompt_template, list):
        # تلاش برای تبدیل لیست به متن
        try:
            return " ".join(str(i) for i in prompt_template)
        except:
            pass

    raise ValueError(f"قالب پرامپت قابل تبدیل به متن نیست. ساختار: {prompt_template}")

# ================= TELEGRAM HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 سلام!\nایده‌ات رو بفرست تا برات پرامپت حرفه‌ای بسازم."
    )
    logger.info("/start received")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info("📩 User message received: %s", user_text)

    status_message = await update.message.reply_text("⏳ در حال ساخت پرامپت...")

    try:
        # استفاده از ترد جداگانه برای جلوگیری از قفل شدن
        config = await asyncio.to_thread(
            lambda: ag.ConfigManager.get_from_registry(
                app_slug="Prompt-Writer",
                environment_slug="development",
            )
        )

        logger.info("✅ Agenta config loaded successfully")

        # گرفتن prompt از config
        prompt_template = config.get("prompt")

        if not prompt_template:
            raise ValueError("❌ کلید 'prompt' در Agenta config پیدا نشد")

        # استفاده از تابع اصلاح شده
        template_text = extract_prompt_text(prompt_template)
        
        # جایگذاری متن کاربر
        if "{{user_idea}}" in template_text:
            final_prompt = template_text.replace("{{user_idea}}", user_text)
        else:
            final_prompt = f"{template_text}\n\nUser Idea: {user_text}"

        logger.info("🧠 Prompt generated successfully")

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
