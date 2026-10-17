"""Natijalarni sahifalarga bo'lish."""

from dataclasses import dataclass

PER_PAGE = 5


@dataclass(frozen=True)
class Page:
    """Bitta sahifa haqidagi ma'lumot. ``number`` 0 dan boshlanadi."""

    number: int
    total_pages: int
    total_items: int
    per_page: int = PER_PAGE

    @property
    def offset(self) -> int:
        """SQL'dagi OFFSET qiymati: nechta qatorni tashlab o'tish kerak."""
        return self.number * self.per_page

    @property
    def has_prev(self) -> bool:
        return self.number > 0

    @property
    def has_next(self) -> bool:
        return self.number + 1 < self.total_pages


def make_page(total_items: int, requested: int, per_page: int = PER_PAGE) -> Page:
    """So'ralgan sahifani hisoblaydi.

    Sahifa raqami chegaradan chiqsa (masalan, e'lon bekor qilingani uchun
    sahifalar kamaygan bo'lsa), eng yaqin mavjud sahifa qaytariladi.
    """
    total_pages = max(1, -(-total_items // per_page))  # yuqoriga yaxlitlash
    number = min(max(requested, 0), total_pages - 1)
    return Page(number=number, total_pages=total_pages, total_items=total_items, per_page=per_page)
