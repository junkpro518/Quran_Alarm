import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scheduler import init_scheduler, cancel_todays_reminders, daily_states
from notion_service import mark_ward_done

logger = logging.getLogger(__name__)


async def done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    callback_data = query.data
    date_key = callback_data.replace("done_", "", 1)

    try:
        cancel_todays_reminders(date_key)
        page_id = daily_states[date_key].page_id
        mark_ward_done(page_id)
    except KeyError:
        logger.warning(
            "done_callback: date_key '%s' not found in daily_states. "
            "The bot may have restarted since the reminder was sent.",
            date_key,
        )

    await query.answer("✅ بارك الله فيك!")
    await query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text="✅ بارك الله فيك! تم تسجيل ورد اليوم 📖",
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🕌 بوت الختمة السنوية يعمل!\n\n"
        "سيتم إرسال ورد اليوم كل 30 دقيقة من الساعة 12 ظهراً حتى منتصف الليل."
    )


async def post_init(application: Application) -> None:
    init_scheduler(application.bot, TELEGRAM_CHAT_ID)
    logger.info("post_init: scheduler initialised.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(
        CallbackQueryHandler(done_callback, pattern="^done_")
    )
    application.add_handler(
        CommandHandler("start", start_command)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
