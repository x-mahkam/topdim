"""Hech bir handler mos kelmagan xabarlar uchun. Bu router eng oxirida ulanadi."""

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from topdim.keyboards import reply
from topdim.locales import uz

router = Router(name="fallback")


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(uz.UNKNOWN_INPUT, reply_markup=reply.main_menu())


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    # Eski yoki noma'lum tugma: "soat" belgisi aylanib qolmasligi uchun javob beramiz
    await callback.answer()
