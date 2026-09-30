import os
import sys
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# مسیر اجرای پایپ‌لاین
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.main import run_pipeline

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام! ویدیوی خام صحبت خودت رو (با گوشی) برام بفرست.\n"
        "اگر سناریوی خاصی داری می‌تونی اون رو در کپشن ویدیو بنویسی، در غیر این صورت از سناریوی پیش‌فرض استفاده می‌شه."
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    video_obj = msg.video or msg.document
    if not video_obj:
        await msg.reply_text("لطفاً یک فایل ویدیویی معتبر ارسال کنید.")
        return

    status_msg = await msg.reply_text("📥 در حال دریافت ویدیو از تلگرام...")

    os.makedirs("assets/raw_videos", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    input_path = "assets/raw_videos/speaker.mp4"
    file = await video_obj.get_file()
    await file.download_to_drive(custom_path=input_path)

    script_text = msg.caption if msg.caption else None

    await status_msg.edit_text("⚙️ ویدیو دریافت شد. شروع مراحل خودکار:\n۱. حذف سکوت‌ها با Silero-VAD\n۲. ساخت و رندر B-Roll\n۳. تدوین چنددوربینه...")

    try:
        # اجرای پایپ‌لاین در ترد پس‌زمینه تا ربات فریز نشود
        loop = asyncio.get_running_loop()
        final_video_path = await loop.run_in_executor(
            None,
            lambda: run_pipeline(
                speaker_path=input_path,
                script_text=script_text,
                output_path="output/final_reel.mp4"
            )
        )

        if final_video_path and os.path.exists(final_video_path):
            await status_msg.edit_text("🚀 رندر با موفقیت تکمیل شد! در حال ارسال به شما...")
            with open(final_video_path, "rb") as vid:
                await msg.reply_video(
                    video=vid,
                    caption="✅ ریلز آماده و تدوین‌شده شما!",
                    supports_streaming=True
                )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ خطایی در فرآیند رندر ویدیو رخ داد.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)}")

def main():
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not set in .env")
        return

    print("🤖 Telegram Bot @mtmnreelbot is running and waiting for videos...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

    app.run_polling()

if __name__ == "__main__":
    main()