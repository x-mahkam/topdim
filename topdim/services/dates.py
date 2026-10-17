"""Sanalar bilan ishlash: foydalanuvchi yozgan sanani tekshirish va formatlash."""

import re
from datetime import date, datetime, timedelta, timezone

# O'zbekistonda yozgi vaqt yo'q, shuning uchun doimiy UTC+5 yetarli.
# (zoneinfo Windows'da qo'shimcha "tzdata" paketini talab qiladi.)
TASHKENT_TZ = timezone(timedelta(hours=5), name="Asia/Tashkent")

# E'lon sanasi shu kundan eski bo'lmasligi kerak
MAX_AGE_DAYS = 365

# 05.10.2026, 5.10.2026, 05/10/2026, 05-10-2026 ko'rinishlari qabul qilinadi
_DATE_RE = re.compile(r"^\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})\s*$")


class DateInputError(ValueError):
    """Sana noto'g'ri kiritilganda. ``reason`` — xato turi."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason  # "format", "future" yoki "too_old"


def today_tashkent() -> date:
    """Toshkent vaqti bo'yicha bugungi sana."""
    return datetime.now(TASHKENT_TZ).date()


def parse_user_date(text: str, today: date) -> date:
    """Foydalanuvchi yozgan sanani tekshiradi va ``date`` obyektiga aylantiradi.

    ``today`` parametr sifatida beriladi — shunda funksiyani test qilish oson.
    Xato bo'lsa ``DateInputError`` ko'tariladi.
    """
    match = _DATE_RE.match(text)
    if not match:
        raise DateInputError("format")

    day, month, year = (int(part) for part in match.groups())
    try:
        value = date(year, month, day)
    except ValueError:  # masalan, 31.02.2026
        raise DateInputError("format") from None

    if value > today:
        raise DateInputError("future")
    if (today - value).days > MAX_AGE_DAYS:
        raise DateInputError("too_old")
    return value


def format_date(value: date) -> str:
    """Sanani o'zbekcha odatiy ko'rinishda qaytaradi: 05.10.2026."""
    return value.strftime("%d.%m.%Y")
