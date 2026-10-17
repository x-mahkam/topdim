"""Inline-tugmalar: xabarning o'ziga biriktiriladi.

Inline tugma bosilganda bot ``callback_data`` satrini oladi. aiogram'ning
``CallbackData`` klasslari bu satrni qulay obyektga aylantiradi, masalan:
``ItemCallback(action="view", item_id=12)`` <-> ``"item:view:12"``.
Telegram cheklovi: callback_data 64 baytdan oshmasligi kerak.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from topdim.db.models import Item, ItemStatus
from topdim.locales import uz
from topdim.services.pagination import Page


class ItemAction:
    """E'lon ustidagi amallar nomi (callback_data ichida yuboriladi)."""

    VIEW = "view"
    ASK_RETURNED = "ask_ret"
    DO_RETURNED = "do_ret"
    ASK_CANCEL = "ask_can"
    DO_CANCEL = "do_can"
    BACK = "back"


class ItemCallback(CallbackData, prefix="item"):
    action: str
    item_id: int


class PageCallback(CallbackData, prefix="page"):
    scope: str  # "search" yoki "my" — qaysi ro'yxat varaqlanmoqda
    number: int


def item_list(items: list[Item], page: Page, scope: str) -> InlineKeyboardMarkup:
    """E'lonlar ro'yxati ostidagi tugmalar: har e'lon uchun raqam + varaqlash."""
    item_buttons = [
        InlineKeyboardButton(
            text=f"#{item.id}",
            callback_data=ItemCallback(action=ItemAction.VIEW, item_id=item.id).pack(),
        )
        for item in items
    ]
    rows = [item_buttons] if item_buttons else []

    nav = []
    if page.has_prev:
        nav.append(
            InlineKeyboardButton(
                text=uz.BTN_PREV,
                callback_data=PageCallback(scope=scope, number=page.number - 1).pack(),
            )
        )
    if page.has_next:
        nav.append(
            InlineKeyboardButton(
                text=uz.BTN_NEXT,
                callback_data=PageCallback(scope=scope, number=page.number + 1).pack(),
            )
        )
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def owner_actions(item: Item) -> InlineKeyboardMarkup | None:
    """E'lon egasi uchun boshqaruv tugmalari (faqat faol e'londa)."""
    if item.status is not ItemStatus.ACTIVE:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=uz.BTN_MARK_RETURNED,
                    callback_data=ItemCallback(action=ItemAction.ASK_RETURNED, item_id=item.id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=uz.BTN_CANCEL_ITEM,
                    callback_data=ItemCallback(action=ItemAction.ASK_CANCEL, item_id=item.id).pack(),
                )
            ],
        ]
    )


def confirm_action(item_id: int, do_action: str, yes_text: str) -> InlineKeyboardMarkup:
    """«Ha, ...» / «Yo'q, orqaga» — tasodifiy bosishdan himoya."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=yes_text,
                    callback_data=ItemCallback(action=do_action, item_id=item_id).pack(),
                ),
                InlineKeyboardButton(
                    text=uz.BTN_NO,
                    callback_data=ItemCallback(action=ItemAction.BACK, item_id=item_id).pack(),
                ),
            ]
        ]
    )
