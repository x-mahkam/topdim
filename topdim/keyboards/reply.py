"""Reply-tugmalar: ekranning pastki qismida, klaviatura o'rnida chiqadi.

Foydalanuvchi bunday tugmani bossa, bot tugmadagi matnni oddiy xabar sifatida
oladi. Shuning uchun handlerlar tugma matnini locales/uz.py'dagi qiymat bilan
solishtiradi.
"""

from collections.abc import Iterable

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from topdim.locales import uz


def _build(rows: list[list[str]], placeholder: str | None = None) -> ReplyKeyboardMarkup:
    """Matnlar ro'yxatidan klaviatura yasaydi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text) for text in row] for row in rows],
        resize_keyboard=True,
        input_field_placeholder=placeholder,
    )


def _chunk(items: list[str], size: int) -> list[list[str]]:
    """Ro'yxatni ``size`` tadan qatorlarga bo'ladi."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def main_menu() -> ReplyKeyboardMarkup:
    """Asosiy menyu."""
    return _build(
        [
            [uz.BTN_LOST, uz.BTN_FOUND],
            [uz.BTN_SEARCH, uz.BTN_MY_ITEMS],
            [uz.BTN_HELP],
        ]
    )


def choices(labels: Iterable[str], columns: int = 2, extra: Iterable[str] = ()) -> ReplyKeyboardMarkup:
    """Variantlar + qo'shimcha tugmalar + har doim oxirida «Bekor qilish»."""
    rows = _chunk(list(labels), columns)
    rows.extend([label] for label in extra)
    rows.append([uz.BTN_CANCEL])
    return _build(rows)


def cancel_only() -> ReplyKeyboardMarkup:
    """Matn kiritish bosqichlari uchun: faqat «Bekor qilish»."""
    return _build([[uz.BTN_CANCEL]], placeholder="Javobingizni yozing…")


def skip_or_cancel() -> ReplyKeyboardMarkup:
    return _build([[uz.BTN_SKIP], [uz.BTN_CANCEL]])


def dates() -> ReplyKeyboardMarkup:
    return choices([uz.BTN_TODAY, uz.BTN_YESTERDAY], extra=[uz.BTN_ENTER_DATE])


def confirm() -> ReplyKeyboardMarkup:
    return _build([[uz.BTN_CONFIRM], [uz.BTN_CANCEL]])
