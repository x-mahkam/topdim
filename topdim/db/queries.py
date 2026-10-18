"""Bazaga so'rovlar. Barcha SQL shu faylda jamlangan.

Har bir funksiya birinchi argument sifatida ``Database`` oladi. Qiymatlar
SQL matniga hech qachon to'g'ridan-to'g'ri qo'shilmaydi — faqat ``?``
o'rinbosarlari orqali beriladi. Bu SQL-injeksiyadan himoya qiladi.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

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


# ---------------------------------------------------------------------------
# Moslashtirish (2-bosqich)
# ---------------------------------------------------------------------------
async def list_match_candidates(db: Database, item: Item, max_days_apart: int) -> list[Item]:
    """Yangi e'longa o'xshash bo'lishi mumkin bo'lgan e'lonlar.

    Bazaning o'zida eng oddiy shartlar bilan saralaymiz (qarama-qarshi tur,
    faol, boshqa egasi, sana oralig'i). Ball esa services/matching.py'da
    hisoblanadi.
    """
    opposite = ItemKind.FOUND if item.kind is ItemKind.LOST else ItemKind.LOST
    date_from = (item.event_date - timedelta(days=max_days_apart)).isoformat()
    date_to = (item.event_date + timedelta(days=max_days_apart)).isoformat()
    rows = await db.fetch_all(
        """
        SELECT * FROM items
        WHERE kind = ? AND status = ? AND owner_id != ?
          AND event_date BETWEEN ? AND ?
        ORDER BY id DESC
        LIMIT 500
        """,
        (opposite.value, ItemStatus.ACTIVE.value, item.owner_id, date_from, date_to),
    )
    return [Item.from_row(row) for row in rows]


async def save_match(db: Database, first: Item, second: Item, score: int) -> bool:
    """Juftlikni saqlaydi. Yangi juftlik bo'lsa True, avval saqlangan bo'lsa False."""
    lost, found = (first, second) if first.kind is ItemKind.LOST else (second, first)
    new_id = await db.execute(
        """
        INSERT OR IGNORE INTO matches (lost_item_id, found_item_id, score, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (lost.id, found.id, score, _now()),
    )
    return new_id > 0


# ---------------------------------------------------------------------------
# Mobil ilovaga kirish (login kodlari va sessiyalar)
# ---------------------------------------------------------------------------
async def create_login_code(db: Database, code: str) -> None:
    await db.execute("INSERT INTO login_codes (code, created_at) VALUES (?, ?)", (code, _now()))


async def get_login_code(db: Database, code: str) -> tuple[int | None, datetime] | None:
    """Kod egasi (hali tasdiqlanmagan bo'lsa None) va yaratilgan vaqti."""
    row = await db.fetch_one("SELECT user_id, created_at FROM login_codes WHERE code = ?", (code,))
    if row is None:
        return None
    return row["user_id"], datetime.fromisoformat(row["created_at"])


async def confirm_login_code(db: Database, code: str, user_id: int) -> bool:
    """Botda tasdiqlangan kodni foydalanuvchiga bog'laydi (faqat bir marta)."""
    await ensure_user(db, user_id)
    changed = await db.execute(
        "UPDATE login_codes SET user_id = ? WHERE code = ? AND user_id IS NULL", (user_id, code)
    )
    return changed > 0


async def delete_login_code(db: Database, code: str) -> None:
    await db.execute("DELETE FROM login_codes WHERE code = ?", (code,))


async def create_session(db: Database, token_hash: str, user_id: int) -> None:
    await db.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at) VALUES (?, ?, ?)",
        (token_hash, user_id, _now()),
    )


async def get_session_user(db: Database, token_hash: str) -> int | None:
    row = await db.fetch_one("SELECT user_id FROM sessions WHERE token_hash = ?", (token_hash,))
    return row["user_id"] if row else None


async def delete_session(db: Database, token_hash: str) -> None:
    await db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
