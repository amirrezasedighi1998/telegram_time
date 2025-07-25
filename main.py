# main.py
import logging
import re
from datetime import datetime, timedelta
import pytz
import asyncio
import os

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # مثل -1002798561239
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # بدون @
TIME_ZONE = "Asia/Tehran"
REPLY_TEXT = "⏰ فقط 30 دقیقه باقی مانده!"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_datetime(text):
    patterns = [
        r'Deadline:\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})',
        r'Deadline:\s*(\d{4})[./-](\d{1,2})[./-](\d{1,2})\s+(\d{1,2}):(\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = list(map(int, match.groups()))
            if pattern.startswith(r'Deadline:\s*(\d{2})'):
                day, month, year, hour, minute = groups
            else:
                year, month, day, hour, minute = groups
            return datetime(year, month, day, hour, minute)
    return None

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if message.chat.id != CHANNEL_ID:
        return

    if not message.text or "Deadline:" not in message.text:
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

        await asyncio.sleep(delay_seconds)

        link = f"https://t.me/{CHANNEL_USERNAME}/{message.message_id}"
        reply_text = f"{REPLY_TEXT}\n\n📌 [مشاهده پیام مرتبط]({link})"

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=reply_text,
            parse_mode="Markdown",
            reply_to_message_id=message.message_id
        )

        logger.info("✅ پیام با موفقیت ارسال شد.")

    except Exception as e:
        logger.error(f"❌ خطا: {e}")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.TEXT, handle_channel_post))
    logger.info("🤖 ربات فعال شد.")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
