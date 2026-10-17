"""«Mening e'lonlarim»: foydalanuvchi faqat o'z e'lonlarini ko'radi."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from topdim.db import queries
from topdim.db.database import Database
from topdim.handlers.utils import reset_state
from topdim.keyboards import inline, reply
from topdim.locales import uz
from topdim.services.cards import format_item_line
from topdim.services.pagination import make_page

router = Router(name="my_items")

SCOPE = "my"


@router.message(F.text == uz.BTN_MY_ITEMS)
async def show_my_items(message: Message, state: FSMContext, db: Database) -> None:
    await reset_state(state)
    text, markup = await render_my_items(db, message.from_user.id, page_number=0)
    # Ro'yxat bo'sh bo'lsa inline tugma yo'q — o'rniga asosiy menyuni qaytaramiz
    await message.answer(text, reply_markup=markup or reply.main_menu())


@router.callback_query(inline.PageCallback.filter(F.scope == SCOPE))
async def change_page(callback: CallbackQuery, callback_data: inline.PageCallback, db: Database) -> None:
    text, markup = await render_my_items(db, callback.from_user.id, callback_data.number)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


async def render_my_items(db: Database, user_id: int, page_number: int) -> tuple[str, InlineKeyboardMarkup | None]:
    total = await queries.count_user_items(db, user_id)
    if total == 0:
        return uz.MY_ITEMS_EMPTY, None

    page = make_page(total, page_number)
    items = await queries.list_user_items(db, user_id, limit=page.per_page, offset=page.offset)
    lines = [uz.MY_ITEMS_HEADER.format(total=total, page=page.number + 1, pages=page.total_pages)]
    lines += [format_item_line(item, show_status=True) for item in items]
    lines.append(uz.RESULTS_HINT)
    return "\n".join(lines), inline.item_list(items, page, SCOPE)
