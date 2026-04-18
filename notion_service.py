import datetime
import logging
from hijri_converter import Hijri
from notion_client import Client
from config import NOTION_TOKEN, NOTION_DATABASE_ID

ARABIC_MONTHS = [
    None, "محرم", "صفر", "ربيع الأول", "ربيع الآخر",
    "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان",
    "رمضان", "شوال", "ذو القعدة", "ذو الحجة",
]
ARABIC_TO_NUM = {name: i for i, name in enumerate(ARABIC_MONTHS) if name}


def _hijri_str_to_gregorian(hijri_str: str) -> datetime.date | None:
    """تحويل نص هجري (مثل 1/ذو القعدة/1447) إلى تاريخ ميلادي."""
    try:
        day_str, month_name, year_str = hijri_str.split("/")
        month_num = ARABIC_TO_NUM.get(month_name.strip())
        if not month_num:
            return None
        day = int(day_str)
        year = int(year_str)
        # بعض الأشهر لا تملك يوم 30 — نحاول بيوم 29 كـ fallback
        for d in [day, 29]:
            try:
                hijri = Hijri(year, month_num, d)
                g = hijri.to_gregorian()
                return datetime.date(g.year, g.month, g.day)
            except Exception:
                continue
        return None
    except Exception:
        return None

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


def get_missed_wards(today_hijri_str: str) -> list[dict]:
    """جلب كل الأوراد السابقة غير المكتملة (تم = False)، باستثناء اليوم."""
    try:
        client = Client(auth=NOTION_TOKEN)
        results = []
        has_more = True
        cursor = None

        while has_more:
            kwargs = {
                "database_id": NOTION_DATABASE_ID,
                "filter": {"property": "تم", "checkbox": {"equals": False}},
            }
            if cursor:
                kwargs["start_cursor"] = cursor

            response = client.databases.query(**kwargs)
            results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            cursor = response.get("next_cursor")

        today = datetime.date.today()
        missed = []
        for result in results:
            hijri_date = result["properties"]["التاريخ"]["rich_text"]
            if not hijri_date:
                continue
            hijri_str = hijri_date[0]["plain_text"]
            if hijri_str == today_hijri_str:
                continue
            ward = result["properties"]["الورد"]["title"][0]["plain_text"]
            # استبعد الأيام المستقبلية
            entry_date = _hijri_str_to_gregorian(hijri_str)
            if entry_date is None:
                logger.warning("Could not parse hijri date '%s', skipping.", hijri_str)
                continue
            if entry_date > today:
                logger.debug("Skipping future ward '%s' (%s).", ward, hijri_str)
                continue
            missed.append({"page_id": result["id"], "ward": ward, "hijri_date": hijri_str})

        return missed

    except Exception as e:
        logger.error("Error fetching missed wards from Notion: %s", e)
        return []


def get_all_wards() -> list[dict]:
    """جلب كل الأوراد مرتبة حسب التاريخ الميلادي."""
    try:
        client = Client(auth=NOTION_TOKEN)
        results = []
        has_more = True
        cursor = None

        while has_more:
            kwargs = {"database_id": NOTION_DATABASE_ID}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = client.databases.query(**kwargs)
            results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            cursor = response.get("next_cursor")

        wards = []
        for result in results:
            hijri_date = result["properties"]["التاريخ"]["rich_text"]
            if not hijri_date:
                continue
            hijri_str = hijri_date[0]["plain_text"]
            ward = result["properties"]["الورد"]["title"][0]["plain_text"]
            done = result["properties"]["تم"]["checkbox"]
            entry_date = _hijri_str_to_gregorian(hijri_str)
            wards.append({
                "page_id": result["id"],
                "ward": ward,
                "hijri_date": hijri_str,
                "done": done,
                "date": entry_date,
            })

        wards.sort(key=lambda x: x["date"] or datetime.date.min)
        return wards

    except Exception as e:
        logger.error("Error fetching all wards from Notion: %s", e)
        return []


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
