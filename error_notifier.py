"""Global error handler that forwards exceptions to OWNER_CHAT_ID on Telegram.

Includes per-error-type cooldown to avoid spamming when the same bug repeats.
"""
import html
import logging
import time
import traceback

from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_CHAT_ID

logger = logging.getLogger(__name__)

# Track last-notification timestamp per error type (sliding 5 min cooldown)
_last_notify: dict[str, float] = {}
_COOLDOWN_SECS = 300


async def notify_owner(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    err_type = type(err).__name__ if err else "Unknown"

    # Log full traceback to stdout regardless
    logger.exception("Unhandled error: %s", err)

    now = time.time()
    last = _last_notify.get(err_type, 0)
    if now - last < _COOLDOWN_SECS:
        logger.info("Skipping owner notification for %s (cooldown)", err_type)
        return
    _last_notify[err_type] = now

    tb = "".join(traceback.format_exception(type(err), err, err.__traceback__)) if err else "n/a"
    tb_short = tb[-1500:]  # Telegram message limit is 4096 — leave buffer for formatting

    ctx_info = ""
    if isinstance(update, Update) and update.effective_user:
        ctx_info = f"\nUser: <code>{update.effective_user.id}</code>"

    msg = (
        f"🚨 <b>Quran Alarm — خطأ</b>\n"
        f"Type: <code>{html.escape(err_type)}</code>\n"
        f"Message: <code>{html.escape(str(err)[:200])}</code>"
        f"{ctx_info}\n\n"
        f"<pre>{html.escape(tb_short)}</pre>"
    )

    try:
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=msg, parse_mode="HTML")
    except Exception as send_err:
        logger.error("Failed to send error notification: %s", send_err)
