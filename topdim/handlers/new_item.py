"""E'lon berish: «Buyumim yo'qoldi» va «Buyum topdim».

Jarayon FSM (Finite State Machine — chekli holatlar mashinasi) orqali
boshqariladi. Har bir savol — alohida holat (State). Foydalanuvchi javob
bergach, javob ``state.update_data`` bilan saqlanadi va keyingi holatga
o'tiladi. Oxirida barcha javoblar bitta e'lon sifatida bazaga yoziladi.

    kategoriya → nom → joy (→ boshqa joy) → sana (→ sanani kiritish)
    → tavsif → rasm → tasdiqlash
"""

from datetime import date, timedelta

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from topdim.db import queries
from topdim.db.database import Database
from topdim.db.models import ItemKind
from topdim.handlers.utils import code_by_label, reset_state, validate_text
from topdim.keyboards import reply
from topdim.locales import uz
from topdim.services.cards import format_card
from topdim.services.dates import MAX_AGE_DAYS, DateInputError, parse_user_date, today_tashkent
from topdim.services.notifications import notify_matches

logger = logging.getLogger(__name__)

router = Router(name="new_item")

# Matn uzunligi chegaralari
TITLE_MIN, TITLE_MAX = 2, 100
PLACE_MIN, PLACE_MAX = 2, 100
DESCRIPTION_MIN, DESCRIPTION_MAX = 5, 700  # rasm izohi 1024 belgidan oshmasligi kerak


class NewItemForm(StatesGroup):
    category = State()
    title = State()
    place = State()
    place_custom = State()
    date = State()
    date_custom = State()
    description = State()
    photo = State()
    confirm = State()


# Matn kutilayotgan holatlar (qolganlarida tugma tanlash kutiladi)
TEXT_STATES = {
    NewItemForm.title.state,
    NewItemForm.place_custom.state,
    NewItemForm.date_custom.state,
    NewItemForm.description.state,
}


# ---------------------------------------------------------------------------
# Boshlash
# ---------------------------------------------------------------------------
@router.message(F.text.in_({uz.BTN_LOST, uz.BTN_FOUND}))
async def start_new_item(message: Message, state: FSMContext) -> None:
    kind = ItemKind.LOST if message.text == uz.BTN_LOST else ItemKind.FOUND
    await reset_state(state)
    await state.update_data(kind=kind.value)
    await state.set_state(NewItemForm.category)
    await message.answer(uz.ASK_CATEGORY[kind], reply_markup=reply.choices(uz.CATEGORIES.values()))


# ---------------------------------------------------------------------------
# Kategoriya va nom
# ---------------------------------------------------------------------------
@router.message(NewItemForm.category, F.text)
async def process_category(message: Message, state: FSMContext) -> None:
    category = code_by_label(uz.CATEGORIES, message.text)
    if category is None:
        await message.answer(uz.CHOOSE_FROM_BUTTONS)
        return
    await state.update_data(category=category)
    await state.set_state(NewItemForm.title)
    await message.answer(uz.ASK_TITLE, reply_markup=reply.cancel_only())


@router.message(NewItemForm.title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    error = validate_text(title, TITLE_MIN, TITLE_MAX)
    if error:
        await message.answer(error)
        return
    await state.update_data(title=title)
    await state.set_state(NewItemForm.place)
    kind = (await state.get_data())["kind"]
    await message.answer(uz.ASK_PLACE[kind], reply_markup=reply.choices(uz.PLACES.values()))


# ---------------------------------------------------------------------------
# Joy
# ---------------------------------------------------------------------------
@router.message(NewItemForm.place, F.text)
async def process_place(message: Message, state: FSMContext) -> None:
    place = code_by_label(uz.PLACES, message.text)
    if place is None:
        await message.answer(uz.CHOOSE_FROM_BUTTONS)
        return
    await state.update_data(place=place, place_note=None)
    if place == "other":
        await state.set_state(NewItemForm.place_custom)
        await message.answer(uz.ASK_PLACE_CUSTOM, reply_markup=reply.cancel_only())
        return
    await ask_date(message, state)


@router.message(NewItemForm.place_custom, F.text)
async def process_place_custom(message: Message, state: FSMContext) -> None:
    note = message.text.strip()
    error = validate_text(note, PLACE_MIN, PLACE_MAX)
    if error:
        await message.answer(error)
        return
    await state.update_data(place_note=note)
    await ask_date(message, state)


# ---------------------------------------------------------------------------
# Sana
# ---------------------------------------------------------------------------
async def ask_date(message: Message, state: FSMContext) -> None:
    await state.set_state(NewItemForm.date)
    kind = (await state.get_data())["kind"]
    await message.answer(uz.ASK_DATE[kind], reply_markup=reply.dates())


@router.message(NewItemForm.date, F.text)
async def process_date(message: Message, state: FSMContext) -> None:
    today = today_tashkent()
    if message.text == uz.BTN_TODAY:
        await save_date_and_continue(message, state, today)
    elif message.text == uz.BTN_YESTERDAY:
        await save_date_and_continue(message, state, today - timedelta(days=1))
    elif message.text == uz.BTN_ENTER_DATE:
        await state.set_state(NewItemForm.date_custom)
        await message.answer(uz.ASK_DATE_CUSTOM, reply_markup=reply.cancel_only())
    else:
        await message.answer(uz.CHOOSE_FROM_BUTTONS)


@router.message(NewItemForm.date_custom, F.text)
async def process_date_custom(message: Message, state: FSMContext) -> None:
    try:
        value = parse_user_date(message.text, today_tashkent())
    except DateInputError as error:
        texts = {
            "format": uz.DATE_BAD_FORMAT,
            "future": uz.DATE_IN_FUTURE,
            "too_old": uz.DATE_TOO_OLD.format(days=MAX_AGE_DAYS),
        }
        await message.answer(texts[error.reason])
        return
    await save_date_and_continue(message, state, value)


async def save_date_and_continue(message: Message, state: FSMContext, value: date) -> None:
    # FSM ma'lumotlarida faqat oddiy turlar (str, int) saqlaymiz — shunda
    # keyinchalik Redis kabi omborga o'tish oson bo'ladi.
    await state.update_data(event_date=value.isoformat())
    await state.set_state(NewItemForm.description)
    await message.answer(uz.ASK_DESCRIPTION, reply_markup=reply.cancel_only())


# ---------------------------------------------------------------------------
# Tavsif va rasm
# ---------------------------------------------------------------------------
@router.message(NewItemForm.description, F.text)
async def process_description(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    error = validate_text(description, DESCRIPTION_MIN, DESCRIPTION_MAX)
    if error:
        await message.answer(error)
        return
    await state.update_data(description=description)
    await state.set_state(NewItemForm.photo)
    await message.answer(uz.ASK_PHOTO, reply_markup=reply.skip_or_cancel())


@router.message(NewItemForm.photo, F.photo)
async def process_photo(message: Message, state: FSMContext) -> None:
    # Telegram rasmni bir nechta o'lchamda yuboradi, oxirgisi — eng kattasi.
    # Rasmning o'zini emas, faqat file_id'sini saqlaymiz.
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await show_preview(message, state)


@router.message(NewItemForm.photo, F.text == uz.BTN_SKIP)
async def skip_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=None)
    await show_preview(message, state)


@router.message(NewItemForm.photo)
async def photo_expected(message: Message) -> None:
    await message.answer(uz.PHOTO_EXPECTED)


# ---------------------------------------------------------------------------
# Tasdiqlash va saqlash
# ---------------------------------------------------------------------------
async def show_preview(message: Message, state: FSMContext) -> None:
    """E'lon qanday ko'rinishini ko'rsatib, tasdiqlashni so'raydi."""
    await state.set_state(NewItemForm.confirm)
    data = await state.get_data()
    card = format_card(
        kind=data["kind"],
        category=data["category"],
        title=data["title"],
        place=data["place"],
        place_note=data.get("place_note"),
        event_date=date.fromisoformat(data["event_date"]),
        description=data["description"],
    )
    text = f"{card}\n\n{uz.ASK_CONFIRM}"
    if data.get("photo_file_id"):
        await message.answer_photo(data["photo_file_id"], caption=text, reply_markup=reply.confirm())
    else:
        await message.answer(text, reply_markup=reply.confirm())


@router.message(NewItemForm.confirm, F.text == uz.BTN_CONFIRM)
async def confirm_item(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    item_id = await queries.create_item(
        db,
        queries.NewItem(
            kind=ItemKind(data["kind"]),
            owner_id=message.from_user.id,
            category=data["category"],
            title=data["title"],
            place=data["place"],
            place_note=data.get("place_note"),
            event_date=date.fromisoformat(data["event_date"]),
            description=data["description"],
            photo_file_id=data.get("photo_file_id"),
        ),
    )
    await reset_state(state)
    await message.answer(uz.ITEM_CREATED.format(item_id=item_id), reply_markup=reply.main_menu())

    # 2-bosqich: o'xshash e'lonlarni qidirish. Bu yerda xato bo'lsa ham
    # e'lon allaqachon saqlangan, shuning uchun foydalanuvchiga ta'sir qilmaydi.
    try:
        await notify_matches(bot, db, await queries.get_item(db, item_id))
    except Exception:
        logger.exception("E'lon #%s uchun moslashtirishda xato", item_id)


# ---------------------------------------------------------------------------
# Kutilmagan javoblar (masalan, matn o'rniga stiker)
# ---------------------------------------------------------------------------
@router.message(NewItemForm.category)
@router.message(NewItemForm.title)
@router.message(NewItemForm.place)
@router.message(NewItemForm.place_custom)
@router.message(NewItemForm.date)
@router.message(NewItemForm.date_custom)
@router.message(NewItemForm.description)
@router.message(NewItemForm.confirm)
async def unexpected_input(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await message.answer(uz.SEND_TEXT_PLEASE if current in TEXT_STATES else uz.CHOOSE_FROM_BUTTONS)
