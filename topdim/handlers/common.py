"""Umumiy buyruqlar: /start, /help, «Bekor qilish» va «Yordam».

Bu router birinchi ulanadi: «Bekor qilish» istalgan bosqichda ishlashi kerak.
"""

from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from topdim.db import queries
from topdim.db.database import Database
from topdim.handlers.utils import reset_state
from topdim.keyboards import reply
from topdim.locales import uz

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database) -> None:
    """Salomlashish va asosiy menyu."""
    await reset_state(state)
    await queries.ensure_user(db, message.from_user.id)
    name = escape(message.from_user.first_name or "talaba", quote=False)
    await message.answer(uz.WELCOME.format(name=name), reply_markup=reply.main_menu())


@router.message(F.text == uz.BTN_CANCEL)
@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    """Istalgan jarayonni to'xtatib, asosiy menyuga qaytaradi."""
    await reset_state(state)
    await message.answer(uz.CANCELLED, reply_markup=reply.main_menu())


@router.message(F.text == uz.BTN_HELP)
@router.message(Command("help"))
async def show_help(message: Message, state: FSMContext) -> None:
    await reset_state(state)
    await message.answer(uz.HELP, reply_markup=reply.main_menu())
