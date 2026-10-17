"""Yo'qolgan va topilgan e'lonlarni avtomatik moslashtirish.

Bu modul faqat hisob-kitob qiladi: bazaga ham, Telegram'ga ham murojaat
qilmaydi. Shuning uchun uni oddiy pytest testlari bilan tekshirish oson.

Ikki e'lon qanchalik o'xshashligi 0..100 ball bilan baholanadi:

    Mezon               Ball
    ------------------  ----------------------------------------------
    Kategoriya bir xil  30
    Nomdagi so'zlar     0..40 (umumiy so'zlar ulushiga qarab)
    Joy bir xil         15
    Sana farqi          ≤1 kun: 15, ≤3 kun: 10, ≤14 kun: 5

Sana farqi 14 kundan oshsa, e'lonlar umuman solishtirilmaydi (ball 0).
Ball ``MATCH_THRESHOLD`` dan oshsa yoki teng bo'lsa — e'lonlar o'xshash.
"""

import os
from dataclasses import dataclass, field

from topdim.db.models import Item, ItemKind, ItemStatus
from topdim.services.text import extract_keywords

# Mezonlar uchun ballar
CATEGORY_POINTS = 30
KEYWORD_POINTS = 40
PLACE_POINTS = 15
DATE_POINTS = ((1, 15), (3, 10), (14, 5))  # (necha kungacha, ball)

MAX_DAYS_APART = 14
MATCH_THRESHOLD = 50

# So'z o'zagi mos kelishi uchun eng kam uzunliklar:
#   "kalit" ~ "kalitlar" (qisqa so'z to'liq boshida, kamida 4 harf);
#   "bekati" ~ "bekatda" (umumiy boshlanish kamida 5 harf).
MIN_STEM_LENGTH = 4
MIN_COMMON_PREFIX = 5

# Nomda ko'p uchraydigan, lekin buyumni ajratib bermaydigan so'zlar
STOPWORDS = frozenset({"va", "bilan", "uchun", "rangli", "rang", "eski", "yangi", "kichik", "katta"})


@dataclass(frozen=True)
class MatchResult:
    """Moslashtirish natijasi: qaysi e'lon, necha ball va nima uchun."""

    item: Item
    score: int
    reasons: dict[str, int] = field(default_factory=dict)


def title_keywords(title: str) -> list[str]:
    """Nomdan solishtirish uchun kalit so'zlarni oladi."""
    return [word for word in extract_keywords(title) if word not in STOPWORDS]


def words_match(a: str, b: str) -> bool:
    """Ikki so'z bir xilmi yoki bir o'zakdanmi.

    O'zbek tilida qo'shimchalar ko'p ("kalit", "kaliti", "kalitlar"), shuning
    uchun so'zlarning boshlanishi (o'zagi) bir xil bo'lsa ham mos deb hisoblaymiz.
    """
    if a == b:
        return True
    shorter, longer = sorted((a, b), key=len)
    if len(shorter) >= MIN_STEM_LENGTH and longer.startswith(shorter):
        return True
    return len(os.path.commonprefix([a, b])) >= MIN_COMMON_PREFIX


def keyword_overlap(first: list[str], second: list[str]) -> float:
    """Umumiy so'zlar ulushi: 0.0 (umuman yo'q) dan 1.0 (to'liq) gacha.

    Qisqaroq ro'yxatga nisbatan hisoblanadi: "hamyon" va "qora charm hamyon"
    — bu 1.0, chunki qisqa nomdagi yagona so'z ikkinchisida bor.
    """
    if not first or not second:
        return 0.0
    shorter, longer = sorted((first, second), key=len)
    common = sum(1 for word in shorter if any(words_match(word, other) for other in longer))
    return common / len(shorter)


def same_place(a: Item, b: Item) -> bool:
    """Joy bir xilmi. "Boshqa joy" bo'lsa, yozilgan matnlar solishtiriladi."""
    if a.place != b.place:
        return False
    if a.place == "other":
        return keyword_overlap(extract_keywords(a.place_note or ""), extract_keywords(b.place_note or "")) > 0
    return True


def date_points(days_apart: int) -> int:
    for max_days, points in DATE_POINTS:
        if days_apart <= max_days:
            return points
    return 0


def score_match(a: Item, b: Item) -> MatchResult:
    """Ikki e'lonning o'xshashlik balini hisoblaydi (natija ``b`` uchun)."""
    days_apart = abs((a.event_date - b.event_date).days)
    if days_apart > MAX_DAYS_APART:
        return MatchResult(item=b, score=0)

    reasons: dict[str, int] = {}
    if a.category == b.category:
        reasons["category"] = CATEGORY_POINTS
    overlap = keyword_overlap(title_keywords(a.title), title_keywords(b.title))
    if overlap:
        reasons["keywords"] = round(KEYWORD_POINTS * overlap)
    if same_place(a, b):
        reasons["place"] = PLACE_POINTS
    reasons["date"] = date_points(days_apart)
    return MatchResult(item=b, score=sum(reasons.values()), reasons=reasons)


def can_match(a: Item, b: Item) -> bool:
    """Faqat qarama-qarshi turdagi, faol va boshqa odamga tegishli e'lonlar."""
    return (
        a.kind != b.kind
        and a.owner_id != b.owner_id
        and a.status is ItemStatus.ACTIVE
        and b.status is ItemStatus.ACTIVE
    )


def find_matches(
    new_item: Item,
    candidates: list[Item],
    threshold: int = MATCH_THRESHOLD,
    limit: int = 5,
) -> list[MatchResult]:
    """Yangi e'longa o'xshash e'lonlarni topadi (eng o'xshashi birinchi)."""
    results = [
        score_match(new_item, candidate)
        for candidate in candidates
        if can_match(new_item, candidate)
    ]
    matches = [result for result in results if result.score >= threshold]
    matches.sort(key=lambda result: (result.score, result.item.id), reverse=True)
    return matches[:limit]


def opposite_kind(kind: ItemKind) -> ItemKind:
    return ItemKind.FOUND if kind is ItemKind.LOST else ItemKind.LOST
