import logging
from notion_client import Client
from config import NOTION_TOKEN, NOTION_DATABASE_ID

logger = logging.getLogger(__name__)


def get_todays_ward(hijri_date_str: str) -> dict | None:
    try:
        client = Client(auth=NOTION_TOKEN)
        response = client.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "التاريخ",
                "rich_text": {"equals": hijri_date_str}
            }
        )
        results = response.get("results", [])
        if not results:
            return None

        result = results[0]
        page_id = result["id"]
        ward = result["properties"]["الورد"]["title"][0]["plain_text"]
        done = result["properties"]["تم"]["checkbox"]

        return {"page_id": page_id, "ward": ward, "done": done}

    except Exception as e:
        logger.error("Error fetching today's ward from Notion: %s", e)
        return None


def mark_ward_done(page_id: str) -> bool:
    try:
        client = Client(auth=NOTION_TOKEN)
        client.pages.update(
            page_id=page_id,
            properties={"تم": {"checkbox": True}}
        )
        return True

    except Exception as e:
        logger.error("Error marking ward as done in Notion (page_id=%s): %s", page_id, e)
        return False
