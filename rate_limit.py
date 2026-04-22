"""Per-user sliding-window rate limiting for telegram handlers.

Wraps any handler. If the user exceeds the limit, a polite message is sent
and the handler is skipped.
"""
import functools
import logging
import time
from collections import defaultdict, deque

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Limits per user_id
PER_MINUTE = 20
PER_HOUR = 200

_minute_window: dict[int, deque] = defaultdict(deque)
_hour_window: dict[int, deque] = defaultdict(deque)
_last_warning: dict[int, float] = {}


def _allowed(user_id: int) -> bool:
    now = time.time()

    mw = _minute_window[user_id]
    while mw and now - mw[0] > 60:
        mw.popleft()
    hw = _hour_window[user_id]
    while hw and now - hw[0] > 3600:
        hw.popleft()

    if len(mw) >= PER_MINUTE or len(hw) >= PER_HOUR:
        return False

    mw.append(now)
    hw.append(now)
    return True


def rate_limited(handler):
    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *a, **kw):
        user = update.effective_user
        if not user:
            return await handler(update, context, *a, **kw)

        if not _allowed(user.id):
            # Warn at most once per 30 seconds per user to avoid a reply flood
            now = time.time()
            if now - _last_warning.get(user.id, 0) > 30:
                _last_warning[user.id] = now
                try:
                    if update.message:
                        await update.message.reply_text(
                            "⏳ تجاوزت الحد المسموح من الرسائل. حاول بعد دقيقة."
                        )
                    elif update.callback_query:
                        await update.callback_query.answer(
                            "⏳ تجاوزت الحد، حاول بعد دقيقة.", show_alert=False
                        )
                except Exception:
                    pass
            logger.info("rate-limited user %s", user.id)
            return
        return await handler(update, context, *a, **kw)
    return wrapper
