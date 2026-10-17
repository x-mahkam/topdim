"""Qidiruv: kategoriya → kalit so'z → sahifalangan natijalar.

Qidiruv parametrlari FSM ma'lumotlarida saqlanadi, inline tugmalarda esa faqat
sahifa raqami yuboriladi (callback_data 64 bayt bilan cheklangan, kalit so'z
esa uzun bo'lishi mumkin).
"""

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from topdim.db import queries
from topdim.db.database import Database
from topdim.handlers.utils import SEARCH_DATA_KEY, code_by_label, reset_state
from topdim.keyboards import inline, reply
from topdim.locales import uz
from topdim.services.cards import format_item_line
from topdim.services.pagination import make_page
from topdim.services.text import extract_keywords

router = Router(name="search")

SCOPE = "search"
KEYWORD_MAX = 60


class SearchForm(StatesGroup):
    category = State()
    keyword = State()


@router.message(F.text == uz.BTN_SEARCH)
async def start_search(message: Message, state: FSMContext) -> None:
    await reset_state(state)
    await state.set_state(SearchForm.category)
    await message.answer(
        uz.SEARCH_ASK_CATEGORY,
        reply_markup=reply.choices(uz.CATEGORIES.values(), extra=[uz.BTN_ALL_CATEGORIES]),
    )


@router.message(SearchForm.category, F.text)
async def process_category(message: Message, state: FSMContext) -> None:
    if message.text == uz.BTN_ALL_CATEGORIES:
        category = None
    else:
        category = code_by_label(uz.CATEGORIES, message.text)
        if category is None:
            await message.answer(uz.CHOOSE_FROM_BUTTONS)
            return
    await state.update_data(search_category=category)
    await state.set_state(SearchForm.keyword)
    await message.answer(uz.SEARCH_ASK_KEYWORD, reply_markup=reply.skip_or_cancel())


@router.message(SearchForm.keyword, F.text)
async def process_keyword(message: Message, state: FSMContext, db: Database) -> None:
    if message.text == uz.BTN_SKIP:
        raw_keyword = ""
    else:
        raw_keyword = message.text.strip()
        if len(raw_keyword) > KEYWORD_MAX:
            await message.answer(uz.SEARCH_KEYWORD_TOO_LONG)
            return

    data = await state.get_data()
    params = {"category": data.get("search_category"), "keywords": extract_keywords(raw_keyword)}

    # Jarayon tugadi: holatni tozalab, qidiruv parametrlarini saqlab qo'yamiz
    await state.clear()
    await state.update_data({SEARCH_DATA_KEY: params})

    await message.answer(describe_query(params), reply_markup=reply.main_menu())
    text, markup = await render_results(db, params, page_number=0)
    await message.answer(text, reply_markup=markup)


@router.message(SearchForm.category)
@router.message(SearchForm.keyword)
async def unexpected_input(message: Message) -> None:
    await message.answer(uz.CHOOSE_FROM_BUTTONS)


@router.callback_query(inline.PageCallback.filter(F.scope == SCOPE))
async def change_page(
    callback: CallbackQuery, callback_data: inline.PageCallback, state: FSMContext, db: Database
) -> None:
    params = (await state.get_data()).get(SEARCH_DATA_KEY)
    if params is None:  # masalan, bot qayta ishga tushgan bo'lsa
        await callback.answer(uz.SEARCH_EXPIRED, show_alert=True)
        return
    text, markup = await render_results(db, params, callback_data.number)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


def describe_query(params: dict) -> str:
    """Foydalanuvchiga nima qidirilayotganini eslatadi."""
    category = uz.CATEGORIES.get(params["category"], uz.BTN_ALL_CATEGORIES)
    text = f"🔎 {category}"
    if params["keywords"]:
        text += f" · «{escape(' '.join(params['keywords']), quote=False)}»"
    return text


async def render_results(db: Database, params: dict, page_number: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Qidiruv natijalarining bitta sahifasini tayyorlaydi."""
    keywords, category = params["keywords"], params["category"]
    total = await queries.count_search_items(db, keywords, category)
    if total == 0:
        return uz.SEARCH_NOTHING_FOUND, None

    page = make_page(total, page_number)
    items = await queries.search_items(db, keywords, category, limit=page.per_page, offset=page.offset)
    lines = [uz.SEARCH_RESULTS_HEADER.format(total=total, page=page.number + 1, pages=page.total_pages)]
    lines += [format_item_line(item) for item in items]
    lines.append(uz.RESULTS_HINT)
    return "\n".join(lines), inline.item_list(items, page, SCOPE)
