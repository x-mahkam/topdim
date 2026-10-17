"""Ma'lumotlar modellari: bazadagi qator Python obyektiga aylanadi."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Mapping


class ItemKind(StrEnum):
    """E'lon turi."""

    LOST = "lost"    # buyum yo'qolgan
    FOUND = "found"  # buyum topilgan


class ItemStatus(StrEnum):
    """E'lon holati. E'lonlar o'chirilmaydi — faqat holati o'zgaradi."""

    ACTIVE = "active"        # faol, qidiruvda ko'rinadi
    RETURNED = "returned"    # buyum egasiga qaytarildi
    CANCELLED = "cancelled"  # egasi e'lonni bekor qildi


@dataclass(frozen=True)
class Item:
    """Bitta e'lon."""

    id: int
    kind: ItemKind
    owner_id: int          # e'lon egasining Telegram user_id'si
    category: str          # locales.uz.CATEGORIES kaliti
    title: str
    place: str             # locales.uz.PLACES kaliti
    place_note: str | None  # "Boshqa joy" tanlansa, foydalanuvchi yozgan joy
    event_date: date       # yo'qolgan yoki topilgan sana
    description: str
    photo_file_id: str | None
    status: ItemStatus
    created_at: datetime

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Item":
        """Bazadan kelgan qatorni Item obyektiga aylantiradi."""
        return cls(
            id=row["id"],
            kind=ItemKind(row["kind"]),
            owner_id=row["owner_id"],
            category=row["category"],
            title=row["title"],
            place=row["place"],
            place_note=row["place_note"],
            event_date=date.fromisoformat(row["event_date"]),
            description=row["description"],
            photo_file_id=row["photo_file_id"],
            status=ItemStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
