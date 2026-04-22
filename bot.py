import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scheduler import init_scheduler, cancel_todays_reminders, daily_states
import health_server
from error_notifier import notify_owner
from rate_limit import rate_limited
import datetime
from hijri_utils import get_hijri_string, get_today_hijri_string
from notion_service import get_all_wards, get_todays_ward, mark_ward_done

logger = logging.getLogger(__name__)


@rate_limited
async def done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    callback_data = query.data
    date_key = callback_data.replace("done_", "", 1)

    cancel_todays_reminders(date_key)

    page_id = None
    state = daily_states.get(date_key)
    if state:
        # ورد اليوم — page_id موجود في الذاكرة
        page_id = state.page_id
    else:
        try:
            # إذا كان date_key تاريخ ميلادي (YYYY-MM-DD) → ابحث في Notion
            date_obj = datetime.date.fromisoformat(date_key)
            hijri_str = get_hijri_string(date_obj)
            ward_data = get_todays_ward(hijri_str)
            if ward_data:
                page_id = ward_data["page_id"]
        except ValueError:
            # date_key هو page_id مباشرة (ورد متأخر)
            page_id = date_key

    if page_id:
        mark_ward_done(page_id)
    else:
        logger.warning("done_callback: could not find page_id for date_key '%s'.", date_key)

    await query.answer("✅ بارك الله فيك!")
    await query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text="✅ بارك الله فيك! تم تسجيل ورد اليوم 📖",
    )


@rate_limited
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.date.today()
    wards = get_all_wards()

    if not wards:
        await update.message.reply_text("❌ لم أتمكن من جلب الأوراد من Notion.")
        return

    past   = [w for w in wards if w["date"] and w["date"] <  today]
    today_ = [w for w in wards if w["date"] and w["date"] == today]
    future = [w for w in wards if w["date"] and w["date"] >  today]

    lines = []

    if today_:
        w = today_[0]
        icon = "✅" if w["done"] else "🔲"
        lines.append(f"📅 *اليوم*\n{icon} صفحات {w['ward']} — {w['hijri_date']}")

    if past:
        lines.append("\n📖 *السابقة*")
        for w in past:
            icon = "✅" if w["done"] else "❌"
            lines.append(f"{icon} صفحات {w['ward']} — {w['hijri_date']}")

    done_past  = sum(1 for w in past  if w["done"])
    done_today = sum(1 for w in today_ if w["done"])
    total_past = len(past) + len(today_)
    lines.append(f"\n📊 *الإجمالي حتى اليوم:* {done_past + done_today}/{total_past}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@rate_limited
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🕌 بوت الختمة السنوية يعمل!\n\n"
        "سيتم إرسال ورد اليوم كل 30 دقيقة من الساعة 12 ظهراً حتى منتصف الليل."
    )


async def post_init(application: Application) -> None:
    init_scheduler(application.bot, TELEGRAM_CHAT_ID)
    logger.info("post_init: scheduler initialised.")


async def post_shutdown(application: Application) -> None:
    """Graceful shutdown: stop the APScheduler cleanly so in-flight jobs finish."""
    import scheduler as scheduler_mod
    sched = scheduler_mod.scheduler
    if sched and sched.running:
        try:
            sched.shutdown(wait=True)
            logger.info("post_shutdown: scheduler stopped cleanly.")
        except Exception as e:
            logger.error("post_shutdown: scheduler shutdown error: %s", e)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Start health-check HTTP server on background thread (for Uptime Kuma)
    health_server.start(port=8080)

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(
        CallbackQueryHandler(done_callback, pattern="^done_")
    )
    application.add_handler(
        CommandHandler("start", start_command)
    )
    application.add_handler(
        CommandHandler("check", check_command)
    )

    application.add_error_handler(notify_owner)

    application.run_polling()


if __name__ == "__main__":
    main()
