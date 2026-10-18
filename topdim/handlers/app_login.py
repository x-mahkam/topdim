"""Mobil ilovaga Telegram orqali kirish.

Ilova foydalanuvchini t.me/<bot>?start=login_<kod> havolasiga yuboradi.
Bot so'raydi: "Ilovaga kirishni tasdiqlaysizmi?". Tasdiqlash tugmasi
majburiy — aks holda kimdir boshqaga havola yuborib, uning nomidan
ilovaga kirib olishi mumkin edi.

Bu router umumiy /start handleridan OLDIN ulanishi kerak.
"""

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from topdim.db import queries
from topdim.db.database import Database
from topdim.locales import uz
from topdim.services.auth import LOGIN_PREFIX, is_code_expired

router = Router(name="app_login")


class LoginCallback(CallbackData, prefix="login"):
    code: str


async def find_valid_code(db: Database, code: str) -> bool:
    """Kod mavjud, eskirmagan va hali tasdiqlanmaganmi?"""
    found = await queries.get_login_code(db, code)
    if found is None:
        return False
    user_id, created_at = found
    return user_id is None and not is_code_expired(created_at, datetime.now(timezone.utc))


@router.message(CommandStart(deep_link=True, magic=F.args.startswith(LOGIN_PREFIX)))
async def ask_login(message: Message, command: CommandObject, db: Database) -> None:
    code = command.args.removeprefix(LOGIN_PREFIX)
    if not await find_valid_code(db, code):
        await message.answer(uz.APP_LOGIN_EXPIRED)
        return
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=uz.BTN_APP_LOGIN_CONFIRM, callback_data=LoginCallback(code=code).pack()
            )
        ]]
    )
    await message.answer(uz.APP_LOGIN_ASK, reply_markup=markup)


@router.callback_query(LoginCallback.filter())
async def confirm_login(callback: CallbackQuery, callback_data: LoginCallback, db: Database) -> None:
    if await find_valid_code(db, callback_data.code) and await queries.confirm_login_code(
        db, callback_data.code, callback.from_user.id
    ):
        await callback.message.edit_text(uz.APP_LOGIN_DONE)
    else:
        await callback.message.edit_text(uz.APP_LOGIN_EXPIRED)
    await callback.answer()
