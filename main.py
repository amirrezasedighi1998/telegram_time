import logging
import re
from datetime import datetime, timedelta
import pytz
import os

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters


# تنظیمات
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TIME_ZONE = "Asia/Tehran"
REPLY_TEXT = "Only 30 minutes left."

# لاگ‌گیری
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_datetime(text):
    # دنبال تمام تاریخ/زمان‌ها بگرد و اولین تطابق رو برگردون
    patterns = [
        r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})',        # dd.mm.yyyy hh:mm
        r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})\s+UTC',  # dd.mm.yyyy hh:mm UTC
        r'(\d{4})[./-](\d{2})[./-](\d{2})\s+(\d{2}):(\d{2})',  # yyyy-mm-dd hh:mm
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                nums = list(map(int, match))
                if pattern.startswith(r'(\d{2})'):
                    day, month, year, hour, minute = nums
                else:
                    year, month, day, hour, minute = nums
                return datetime(year, month, day, hour, minute)
            except ValueError:
                continue

    return None


async def schedule_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    await context.bot.send_message(
        chat_id=chat_id,
        text=REPLY_TEXT,
        parse_mode="Markdown",
        reply_to_message_id=message_id
    )
    logger.info("✅ پیام با موفقیت ارسال شد.")


async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if message.chat.id != CHANNEL_ID:
        return

    if not message.text:
        return

    event_datetime = extract_datetime(message.text)
    if not event_datetime:
        logger.info("⛔️ تاریخ پیدا نشد.")
        return

    try:
        tz = pytz.timezone(TIME_ZONE)
        event_datetime = tz.localize(event_datetime)
        scheduled_time = event_datetime + timedelta(hours=3)
        now = datetime.now(tz)
        delay_seconds = int((scheduled_time - now).total_seconds())

        if delay_seconds < 600:
            logger.warning("⛔️ زمان کمتر از ۱۰ دقیقه فاصله داره.")
            return

        logger.info(f"⏳ پیام زمان‌بندی شده در {delay_seconds} ثانیه دیگه ارسال میشه")

        context.application.create_task(
            schedule_message(context, CHANNEL_ID, message.message_id, delay_seconds)
        )

    except Exception as e:
        logger.error(f"❌ خطا: {e}")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.TEXT, handle_channel_post))
    logger.info("🤖 ربات فعال شد.")
    app.run_polling()


if __name__ == '__main__':
    main()
