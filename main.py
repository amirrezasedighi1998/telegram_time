import logging
import re
import json
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import pytz

# تنظیمات
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
REPLY_TEXT = "Only 30 minutes left."
TASKS_FILE = "tasks.json"
IRAN_TZ = pytz.timezone("Asia/Tehran")

# لاگ‌گیری
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# زمان‌بندی
scheduler = AsyncIOScheduler()

def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r") as f:
        return json.load(f)

def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f)

def add_task(task):
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)

def remove_task(message_id):
    tasks = load_tasks()
    tasks = [t for t in tasks if t["message_id"] != message_id]
    save_tasks(tasks)

def extract_datetime(text):
    patterns = [
        r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})',
        r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})\s+UTC',
        r'(\d{4})[./-](\d{2})[./-](\d{2})\s+(\d{2}):(\d{2})',
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

async def send_scheduled_message(chat_id, message_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=REPLY_TEXT,
            parse_mode="Markdown",
            reply_to_message_id=message_id
        )
        logger.info(f"✅ پیام با موفقیت برای پیام {message_id} ارسال شد.")
        remove_task(message_id)
    except Exception as e:
        logger.error(f"❌ خطا در ارسال پیام زمان‌بندی‌شده: {e}")

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message or not message.text or not message.chat:
        return
    if message.chat.id != CHANNEL_ID:
        return

    logger.info(f"📩 پیام دریافت‌شده: {message.text}")

    # تاریخ پیام را پیدا کن
    event_datetime = extract_datetime(message.text)
    if not event_datetime:
        logger.info("⛔️ تاریخ پیدا نشد.")
        return

    # تبدیل زمان به تایم‌زون ایران
    event_datetime_tehran = IRAN_TZ.localize(event_datetime)

    # زمان ارسال: ۳ ساعت بعد
    scheduled_time = event_datetime_tehran + timedelta(hours=3)
    now = datetime.now(IRAN_TZ)

    delay_seconds = int((scheduled_time - now).total_seconds())
    if delay_seconds < 600:
        logger.warning("⛔️ زمان کمتر از ۱۰ دقیقه فاصله داره.")
        return

    logger.info(f"📅 زمان رویداد (ایران): {event_datetime_tehran}")
    logger.info(f"⏰ زمان ارسال برنامه‌ریزی‌شده (ایران): {scheduled_time}")

    scheduler.add_job(
        send_scheduled_message,
        trigger="date",
        run_date=scheduled_time,
        args=[CHANNEL_ID, message.message_id, context]
    )

    add_task({
        "message_id": message.message_id,
        "scheduled_time": scheduled_time.isoformat()
    })

async def post_init(application: Application):
    scheduler.start()
    now = datetime.now(IRAN_TZ)
    for task in load_tasks():
        run_time = datetime.fromisoformat(task["scheduled_time"])
        if run_time.tzinfo is None:
            run_time = IRAN_TZ.localize(run_time)
        if run_time > now:
            scheduler.add_job(
                send_scheduled_message,
                trigger="date",
                run_date=run_time,
                args=[CHANNEL_ID, task["message_id"], application]
            )
            logger.info(f"🔄 تسک برای پیام {task['message_id']} بازیابی شد.")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.TEXT, handle_channel_post))
    logger.info("🤖 ربات فعال شد.")
    app.run_polling()

if __name__ == '__main__':
    main()
