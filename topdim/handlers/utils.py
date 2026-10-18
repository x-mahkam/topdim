"""Handlerlar uchun umumiy yordamchi funksiyalar."""

from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

# Oxirgi qidiruv parametrlari FSM ma'lumotlarida shu kalit ostida saqlanadi
SEARCH_DATA_KEY = "search"


async def reset_state(state: FSMContext) -> None:
    """Joriy jarayonni (FSM) tozalaydi, lekin oxirgi qidiruvni saqlab qoladi.

    Shunda foydalanuvchi e'lon berib bo'lgach ham eski qidiruv natijalarini
    varaqlay oladi.
    """
    data = await state.get_data()
    search = data.get(SEARCH_DATA_KEY)
    await state.clear()
    if search is not None:
        await state.update_data({SEARCH_DATA_KEY: search})


def code_by_label(mapping: dict[str, str], label: str) -> str | None:
    """Tugma matni bo'yicha kodni topadi: "🔑 Kalit" -> "keys"."""
    for code, text in mapping.items():
        if text == label:
            return code
    return None


async def edit_card(message: Message, text: str, markup: InlineKeyboardMarkup | None) -> None:
    """Kartochkani yangilaydi. Rasmli xabarda matn ``caption`` ichida turadi."""
    if message.photo:
        await message.edit_caption(caption=text, reply_markup=markup)
    else:
        await message.edit_text(text, reply_markup=markup)
