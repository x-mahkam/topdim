"""E'lonni foydalanuvchiga ko'rsatish uchun matn tayyorlash.

Foydalanuvchi yozgan har bir matn ``html.escape`` orqali o'tkaziladi:
aks holda kimdir "<b>" kabi teglar yozib, xabar ko'rinishini buzishi mumkin.
E'lon egasi haqida hech qanday ma'lumot (ism, username, raqam) ko'rsatilmaydi.
"""

from datetime import date
from html import escape

from topdim.db.models import Item
from topdim.locales import uz
from topdim.services.dates import format_date

# Ro'yxatda nom shu uzunlikdan oshsa qisqartiriladi
LIST_TITLE_MAX = 40


def place_label(place: str, place_note: str | None) -> str:
    """Joy nomi. "Boshqa joy" bo'lsa, foydalanuvchi yozgan matn ko'rsatiladi."""
    if place_note:
        return escape(place_note, quote=False)
    return uz.PLACES.get(place, place)


def format_card(
    *,
    kind: str,
    category: str,
    title: str,
    place: str,
    place_note: str | None,
    event_date: date,
    description: str,
    item_id: int | None = None,
    status: str | None = None,
) -> str:
    """E'lon kartochkasi matni.

    Tasdiqlashdan oldingi ko'rinishda hali ID va holat yo'q, shuning uchun
    ular ixtiyoriy.
    """
    header = f"<b>{uz.KIND_TITLES[kind]}</b>"
    if item_id is not None:
        header += uz.CARD_ID.format(item_id=item_id)

    lines = [
        header,
        "",
        uz.CARD_TITLE.format(title=escape(title, quote=False)),
        uz.CARD_CATEGORY.format(category=uz.CATEGORIES.get(category, category)),
        uz.CARD_PLACE.format(place=place_label(place, place_note)),
        uz.CARD_DATE[kind].format(date=format_date(event_date)),
        uz.CARD_DESCRIPTION.format(description=escape(description, quote=False)),
    ]
    if status is not None:
        lines.append(uz.CARD_STATUS.format(status=uz.STATUS_TITLES[status]))
    return "\n".join(lines)


def format_item_card(item: Item) -> str:
    """Bazadagi e'lon uchun to'liq kartochka."""
    return format_card(
        kind=item.kind,
        category=item.category,
        title=item.title,
        place=item.place,
        place_note=item.place_note,
        event_date=item.event_date,
        description=item.description,
        item_id=item.id,
        status=item.status,
    )


def format_item_line(item: Item, show_status: bool = False) -> str:
    """Ro'yxatdagi bitta qator: «🔴 #12 Qora hamyon — Kutubxona, 05.10.2026»."""
    title = item.title
    if len(title) > LIST_TITLE_MAX:
        title = title[: LIST_TITLE_MAX - 1] + "…"
    line = (
        f"{uz.KIND_SHORT[item.kind]} <b>#{item.id}</b> {escape(title, quote=False)} — "
        f"{place_label(item.place, item.place_note)}, {format_date(item.event_date)}"
    )
    if show_status:
        line += f"\n      {uz.STATUS_TITLES[item.status]}"
    return line
