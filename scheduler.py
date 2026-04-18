from dataclasses import dataclass
from datetime import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from config import TIMEZONE
from hijri_utils import get_today_hijri_string
from notion_service import get_todays_ward

logger = logging.getLogger(__name__)


@dataclass
class DailyState:
    ward: str
    page_id: str
    done: bool = False
    interval_job_id: str | None = None


daily_states: dict[str, DailyState] = {}
scheduler: AsyncIOScheduler | None = None


def init_scheduler(bot, chat_id: str) -> AsyncIOScheduler:
    global scheduler
    tz = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    scheduler.add_job(
        daily_reminder_job,
        trigger=CronTrigger(hour=12, minute=0, timezone=tz),
        args=[bot, chat_id],
        id="daily_reminder",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started. Daily reminder job set for 12:00 %s.", TIMEZONE)
    return scheduler


async def daily_reminder_job(bot, chat_id: str) -> None:
    global scheduler

    hijri_str = get_today_hijri_string()
    ward_data = get_todays_ward(hijri_str)

    if ward_data is None:
        logger.warning("No ward found for today (%s). Skipping reminder.", hijri_str)
        return

    if ward_data["done"]:
        logger.info("Ward for today (%s) is already done. Skipping reminder.", hijri_str)
        return

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    today_gregorian_str = now.strftime("%Y-%m-%d")

    ward_str = ward_data["ward"]
    page_id = ward_data["page_id"]

    state = DailyState(ward=ward_str, page_id=page_id)
    daily_states[today_gregorian_str] = state

    job_id = f"reminder_{today_gregorian_str}"

    # End of the current day at 23:59:59, timezone-aware
    end_date = tz.localize(
        datetime(now.year, now.month, now.day, 23, 59, 59)
    )

    scheduler.add_job(
        send_reminder,
        trigger=IntervalTrigger(minutes=30, start_date=now, end_date=end_date, timezone=tz),
        args=[bot, chat_id, ward_str, today_gregorian_str],
        id=job_id,
        replace_existing=True,
        next_run_time=now,
    )

    state.interval_job_id = job_id
    logger.info(
        "Scheduled interval reminders for ward '%s' (date_key=%s, job_id=%s).",
        ward_str, today_gregorian_str, job_id,
    )


async def send_reminder(bot, chat_id: str, ward: str, date_key: str) -> None:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="✅ تم", callback_data=f"done_{date_key}")]]
    )
    text = f"📖 ورد اليوم: صفحات {ward}\n\nاضغط ✅ تم بعد الانتهاء من القراءة"

    await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    logger.info("Reminder sent for date_key=%s.", date_key)


def cancel_todays_reminders(date_key: str) -> None:
    global scheduler

    state = daily_states.get(date_key)
    if state is None:
        logger.warning("cancel_todays_reminders: no state found for date_key=%s.", date_key)
        return

    job_id = state.interval_job_id
    if job_id and scheduler:
        job = scheduler.get_job(job_id)
        if job:
            job.remove()
            logger.info("Removed interval job '%s'.", job_id)
        else:
            logger.warning("Job '%s' not found in scheduler (may have already ended).", job_id)

    state.done = True
    logger.info("Marked daily state as done for date_key=%s.", date_key)
