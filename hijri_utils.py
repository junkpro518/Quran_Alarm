import datetime
from hijri_converter import Gregorian

ARABIC_MONTHS = [
    None,  # index 0 unused
    "محرم",
    "صفر",
    "ربيع الأول",
    "ربيع الآخر",
    "جمادى الأولى",
    "جمادى الآخرة",
    "رجب",
    "شعبان",
    "رمضان",
    "شوال",
    "ذو القعدة",
    "ذو الحجة",
]


def get_today_hijri_string() -> str:
    today = datetime.date.today()
    hijri = Gregorian(today.year, today.month, today.day).to_hijri()
    month_name = ARABIC_MONTHS[hijri.month]
    return f"{hijri.day}/{month_name}/{hijri.year}"
