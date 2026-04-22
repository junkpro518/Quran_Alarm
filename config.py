import os
from dotenv import load_dotenv

load_dotenv()

_required_vars = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "NOTION_TOKEN",
    "NOTION_DATABASE_ID",
]

_missing = [var for var in _required_vars if not os.getenv(var)]
if _missing:
    raise ValueError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Please set them in your .env file or environment."
    )

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]
# OWNER_CHAT_ID: where error notifications are sent. Defaults to TELEGRAM_CHAT_ID.
OWNER_CHAT_ID: str = os.getenv("OWNER_CHAT_ID", os.environ["TELEGRAM_CHAT_ID"])
NOTION_TOKEN: str = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID: str = os.environ["NOTION_DATABASE_ID"]
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Riyadh")
