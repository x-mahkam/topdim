"""Bazaga so'rovlar. Barcha SQL shu faylda jamlangan.

Har bir funksiya birinchi argument sifatida ``Database`` oladi. Qiymatlar
SQL matniga hech qachon to'g'ridan-to'g'ri qo'shilmaydi — faqat ``?``
o'rinbosarlari orqali beriladi. Bu SQL-injeksiyadan himoya qiladi.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from topdim.db.database import Database
from topdim.db.models import Item, ItemKind, ItemStatus
from topdim.locales import uz
from topdim.services.text import normalize


@dataclass(frozen=True)
class NewItem:
    """Yangi e'lon uchun foydalanuvchidan yig'ilgan ma'lumotlar."""

    kind: ItemKind
    owner_id: int
    category: str
    title: str
    place: str
    place_note: str | None
    event_date: date
    description: str
    photo_file_id: str | None


def _now() -> str:
    """Hozirgi UTC vaqt ISO formatda."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _escape_like(value: str) -> str:
    """LIKE uchun maxsus belgilarni (%, _) oddiy belgiga aylantiradi."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ---------------------------------------------------------------------------
# Foydalanuvchilar
# ---------------------------------------------------------------------------
async def ensure_user(db: Database, user_id: int) -> None:
    """Foydalanuvchini bazaga qo'shadi (agar hali bo'lmasa).

    Faqat Telegram ID saqlanadi: ism, username yoki telefon raqami saqlanmaydi.
    """
    await db.execute(
        "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
        (user_id, _now()),
    )


# ---------------------------------------------------------------------------
# E'lonlar
# ---------------------------------------------------------------------------
async def create_item(db: Database, item: NewItem) -> int:
    """Yangi e'lon yaratadi va uning ID'sini qaytaradi."""
    await ensure_user(db, item.owner_id)
    now = _now()
    # Qidiruv nom, tavsif va joy bo'yicha ishlaydi (legacy/Topdim.py'dagidek)
    place = item.place_note or uz.PLACES.get(item.place, "")
    search_text = normalize(" ".join(filter(None, [item.title, item.description, place])))
    return await db.execute(
        """
        INSERT INTO items (kind, owner_id, category, title, place, place_note,
                           event_date, description, photo_file_id, search_text,
                           status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.kind.value, item.owner_id, item.category, item.title, item.place,
            item.place_note, item.event_date.isoformat(), item.description,
            item.photo_file_id, search_text, ItemStatus.ACTIVE.value, now, now,
        ),
    )


async def get_item(db: Database, item_id: int) -> Item | None:
    row = await db.fetch_one("SELECT * FROM items WHERE id = ?", (item_id,))
    return Item.from_row(row) if row else None


def _search_conditions(keywords: list[str], category: str | None) -> tuple[str, list]:
    """Qidiruv uchun WHERE qismini va parametrlarini tuzadi.

    Har bir kalit so'z nom/tavsifda bo'lishi shart (AND).
    """
    conditions = ["status = ?"]
    params: list = [ItemStatus.ACTIVE.value]
    if category:
        conditions.append("category = ?")
        params.append(category)
    for word in keywords:
        conditions.append("search_text LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(word)}%")
    return " AND ".join(conditions), params


async def count_search_items(db: Database, keywords: list[str], category: str | None) -> int:
    where, params = _search_conditions(keywords, category)
    row = await db.fetch_one(f"SELECT COUNT(*) AS n FROM items WHERE {where}", params)
    return row["n"] if row else 0


async def search_items(
    db: Database, keywords: list[str], category: str | None, limit: int, offset: int
) -> list[Item]:
    """Faol e'lonlarni qidiradi. Eng yangilari birinchi chiqadi."""
    where, params = _search_conditions(keywords, category)
    rows = await db.fetch_all(
        f"SELECT * FROM items WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    return [Item.from_row(row) for row in rows]


async def count_user_items(db: Database, owner_id: int) -> int:
    row = await db.fetch_one("SELECT COUNT(*) AS n FROM items WHERE owner_id = ?", (owner_id,))
    return row["n"] if row else 0


async def list_user_items(db: Database, owner_id: int, limit: int, offset: int) -> list[Item]:
    """Foydalanuvchining barcha e'lonlari: avval faollari, keyin yangilari."""
    rows = await db.fetch_all(
        """
        SELECT * FROM items WHERE owner_id = ?
        ORDER BY (status = 'active') DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        (owner_id, limit, offset),
    )
    return [Item.from_row(row) for row in rows]


async def close_item(db: Database, item_id: int, owner_id: int, new_status: ItemStatus) -> bool:
    """Faol e'lonni yopadi ("qaytarildi" yoki "bekor qilindi").

    Shart ichida ``owner_id`` ham tekshiriladi — shunda begona odam
    birovning e'lonini o'zgartira olmaydi. Muvaffaqiyatli bo'lsa True.
    """
    if new_status is ItemStatus.ACTIVE:
        raise ValueError("close_item faqat e'lonni yopish uchun")
    changed = await db.execute(
        "UPDATE items SET status = ?, updated_at = ? WHERE id = ? AND owner_id = ? AND status = ?",
        (new_status.value, _now(), item_id, owner_id, ItemStatus.ACTIVE.value),
    )
    return changed > 0
