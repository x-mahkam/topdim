"""Botni boshidan oxirigacha tekshiruvchi testlar.

Haqiqiy Telegram o'rniga ``FakeSession`` ishlatiladi: bot yuborgan har bir
so'rov (sendMessage, editMessageText, ...) ro'yxatga yoziladi, javob esa
soxta bo'ladi. Shunday qilib handlerlarni token va internetsiz sinaymiz.
"""

from datetime import datetime, timedelta
from itertools import count

import pytest
from aiogram import Bot
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageCaption,
    EditMessageReplyMarkup,
    EditMessageText,
    SendMessage,
    SendPhoto,
    TelegramMethod,
)
from aiogram.types import CallbackQuery, Chat, Message, PhotoSize, Update, User

from fakes import FakeSession

from topdim.bot import create_dispatcher
from topdim.config import Config
from topdim.db import queries
from topdim.db.models import ItemKind, ItemStatus
from topdim.keyboards.inline import ItemAction, ItemCallback, PageCallback
from topdim.locales import uz
from topdim.services.dates import format_date, today_tashkent


_DISPATCHER = None


def get_dispatcher(db):
    """Dispatcher bir marta yaratiladi: routerlarni faqat bir marta ulash mumkin.

    Har bir test uchun bazani almashtirib, FSM xotirasini tozalaymiz.
    """
    global _DISPATCHER
    if _DISPATCHER is None:
        _DISPATCHER = create_dispatcher(db, Config(bot_token="x", admin_ids=frozenset(), db_path=":memory:"))
    _DISPATCHER["db"] = db
    _DISPATCHER.storage.storage.clear()
    return _DISPATCHER


class Harness:
    """Foydalanuvchi nomidan botga xabar yuborish uchun yordamchi."""

    def __init__(self, db) -> None:
        self.session = FakeSession()
        self.bot = Bot("123456:TEST", session=self.session)
        self.dp = get_dispatcher(db)
        self._update_ids = count(1)

    def _user(self, user_id: int) -> User:
        return User(id=user_id, is_bot=False, first_name="Ali")

    def _message(self, user_id: int, **fields) -> Message:
        return Message(
            message_id=next(self._update_ids),
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            from_user=self._user(user_id),
            **fields,
        )

    async def _feed(self, **update_fields) -> list[TelegramMethod]:
        start = len(self.session.requests)
        await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), **update_fields))
        return self.session.requests[start:]

    async def text(self, user_id: int, text: str) -> list[TelegramMethod]:
        return await self._feed(message=self._message(user_id, text=text))

    async def photo(self, user_id: int, file_id: str) -> list[TelegramMethod]:
        photo = [PhotoSize(file_id=file_id, file_unique_id=file_id, width=100, height=100)]
        return await self._feed(message=self._message(user_id, photo=photo))

    async def press(self, user_id: int, data: str, with_photo: bool = False) -> list[TelegramMethod]:
        extra = {"photo": [PhotoSize(file_id="p", file_unique_id="p", width=1, height=1)]} if with_photo else {"text": "card"}
        message = Message(
            message_id=500, date=datetime.now(), chat=Chat(id=user_id, type="private"), **extra
        )
        callback = CallbackQuery(
            id=str(next(self._update_ids)), from_user=self._user(user_id),
            chat_instance="ci", message=message, data=data,
        )
        return await self._feed(callback_query=callback)


def last_text(requests: list[TelegramMethod]) -> str:
    """Bot yuborgan oxirgi matn yoki rasm izohi."""
    for method in reversed(requests):
        if isinstance(method, SendMessage):
            return method.text
        if isinstance(method, SendPhoto):
            return method.caption
        if isinstance(method, (EditMessageText,)):
            return method.text
        if isinstance(method, EditMessageCaption):
            return method.caption
    raise AssertionError(f"Matnli javob yo'q: {requests}")


def keyboard_texts(method) -> list[str]:
    markup = method.reply_markup
    rows = getattr(markup, "keyboard", None) or getattr(markup, "inline_keyboard", None) or []
    return [button.text for row in rows for button in row]


@pytest.fixture
async def harness(db):
    h = Harness(db)
    yield h
    await h.bot.session.close()


USER, OTHER = 101, 202


async def create_lost_wallet(h: Harness, user_id: int = USER) -> None:
    """To'liq e'lon berish jarayoni (rasmsiz)."""
    await h.text(user_id, uz.BTN_LOST)
    await h.text(user_id, uz.CATEGORIES["bag"])
    await h.text(user_id, "Qora charm hamyon")
    await h.text(user_id, uz.PLACES["library"])
    await h.text(user_id, uz.BTN_TODAY)
    await h.text(user_id, "Ichida talaba guvohnomasi bor")
    await h.text(user_id, uz.BTN_SKIP)
    await h.text(user_id, uz.BTN_CONFIRM)


async def test_start_shows_main_menu(harness):
    requests = await harness.text(USER, "/start")
    assert "TOPDIM" in last_text(requests)
    buttons = keyboard_texts(requests[-1])
    assert {uz.BTN_LOST, uz.BTN_FOUND, uz.BTN_SEARCH, uz.BTN_MY_ITEMS, uz.BTN_HELP} <= set(buttons)


async def test_full_lost_item_flow(harness, db):
    await harness.text(USER, uz.BTN_LOST)
    await harness.text(USER, uz.CATEGORIES["bag"])
    await harness.text(USER, "Qora charm hamyon")
    await harness.text(USER, uz.PLACES["library"])
    await harness.text(USER, uz.BTN_YESTERDAY)
    await harness.text(USER, "Ichida talaba guvohnomasi bor")
    preview = await harness.text(USER, uz.BTN_SKIP)
    assert uz.ASK_CONFIRM in last_text(preview)
    assert "Qora charm hamyon" in last_text(preview)

    done = await harness.text(USER, uz.BTN_CONFIRM)
    assert "#1" in last_text(done)

    item = await queries.get_item(db, 1)
    assert item.owner_id == USER and item.category == "bag" and item.place == "library"
    assert item.event_date == today_tashkent() - timedelta(days=1)


async def test_found_item_with_custom_place_date_and_photo(harness, db):
    await harness.text(USER, uz.BTN_FOUND)
    await harness.text(USER, uz.CATEGORIES["keys"])
    await harness.text(USER, "Kalitlar")
    await harness.text(USER, uz.PLACES["other"])
    await harness.text(USER, "Avtobus bekati")
    await harness.text(USER, uz.BTN_ENTER_DATE)

    bad = await harness.text(USER, "31.02.2026")
    assert last_text(bad) == uz.DATE_BAD_FORMAT
    day = today_tashkent() - timedelta(days=3)
    await harness.text(USER, format_date(day))
    await harness.text(USER, "Uchta kalit, qizil brelok")
    preview = await harness.photo(USER, "photo-123")
    assert isinstance(preview[-1], SendPhoto) and preview[-1].photo == "photo-123"
    await harness.text(USER, uz.BTN_CONFIRM)

    item = await queries.get_item(db, 1)
    assert item.place == "other" and item.place_note == "Avtobus bekati"
    assert item.event_date == day and item.photo_file_id == "photo-123"


async def test_validation_errors_keep_user_on_same_step(harness, db):
    await harness.text(USER, uz.BTN_LOST)
    assert last_text(await harness.text(USER, "Noma'lum kategoriya")) == uz.CHOOSE_FROM_BUTTONS
    await harness.text(USER, uz.CATEGORIES["electronics"])
    assert "Juda qisqa" in last_text(await harness.text(USER, "A"))
    await harness.text(USER, "Samsung telefoni")
    await harness.text(USER, uz.PLACES["gym"])
    await harness.text(USER, uz.BTN_TODAY)
    assert last_text(await harness.text(USER, "Qo'ng'iroq qiling: +998 90 123 45 67")) == uz.CONTAINS_PHONE
    await harness.text(USER, "Qora g'ilofda")
    assert last_text(await harness.text(USER, "rasm yo'q")) == uz.PHOTO_EXPECTED


async def test_cancel_in_the_middle(harness, db):
    await harness.text(USER, uz.BTN_FOUND)
    await harness.text(USER, uz.CATEGORIES["book"])
    requests = await harness.text(USER, uz.BTN_CANCEL)
    assert last_text(requests) == uz.CANCELLED
    assert await queries.count_user_items(db, USER) == 0
    # Holat tozalangan: endi oddiy matn tushunarsiz xabar hisoblanadi
    assert last_text(await harness.text(USER, "Fizika kitobi")) == uz.UNKNOWN_INPUT


async def test_search_with_pagination(harness, db):
    for n in range(7):
        await queries.create_item(db, queries.NewItem(
            kind=ItemKind.FOUND, owner_id=OTHER, category="book", title=f"Fizika kitobi {n}",
            place="library", place_note=None, event_date=today_tashkent(),
            description="Darslik", photo_file_id=None,
        ))

    await harness.text(USER, uz.BTN_SEARCH)
    await harness.text(USER, uz.CATEGORIES["book"])
    results = await harness.text(USER, "fizika")
    text = last_text(results)
    assert "7</b> ta" in text and "1/2" in text
    assert uz.BTN_NEXT in keyboard_texts(results[-1])

    page2 = await harness.press(USER, PageCallback(scope="search", number=1).pack())
    edit = next(m for m in page2 if isinstance(m, EditMessageText))
    assert "2/2" in edit.text and uz.BTN_PREV in keyboard_texts(edit)

    nothing = await harness.text(USER, uz.BTN_SEARCH)
    await harness.text(USER, uz.BTN_ALL_CATEGORIES)
    nothing = await harness.text(USER, "velosiped")
    assert last_text(nothing) == uz.SEARCH_NOTHING_FOUND


async def test_my_items_mark_returned(harness, db):
    await create_lost_wallet(harness)
    listing = await harness.text(USER, uz.BTN_MY_ITEMS)
    assert "Qora charm hamyon" in last_text(listing)

    view = await harness.press(USER, ItemCallback(action=ItemAction.VIEW, item_id=1).pack())
    assert uz.BTN_MARK_RETURNED in keyboard_texts(view[0])

    ask = await harness.press(USER, ItemCallback(action=ItemAction.ASK_RETURNED, item_id=1).pack())
    assert isinstance(ask[0], EditMessageReplyMarkup)
    assert uz.BTN_YES_RETURNED in keyboard_texts(ask[0])

    done = await harness.press(USER, ItemCallback(action=ItemAction.DO_RETURNED, item_id=1).pack())
    assert uz.STATUS_TITLES["returned"] in last_text(done)
    assert (await queries.get_item(db, 1)).status is ItemStatus.RETURNED


async def test_other_user_cannot_manage_or_see_closed_item(harness, db):
    await create_lost_wallet(harness, USER)

    # Begona foydalanuvchi faol e'lonni ko'radi, lekin boshqaruv tugmalarisiz
    view = await harness.press(OTHER, ItemCallback(action=ItemAction.VIEW, item_id=1).pack())
    assert view[0].reply_markup is None
    assert str(USER) not in view[0].text  # egasi haqida ma'lumot yo'q

    # Soxta callback bilan bekor qilishga urinish
    attempt = await harness.press(OTHER, ItemCallback(action=ItemAction.DO_CANCEL, item_id=1).pack())
    assert isinstance(attempt[0], AnswerCallbackQuery) and attempt[0].text == uz.ITEM_NOT_YOURS
    assert (await queries.get_item(db, 1)).status is ItemStatus.ACTIVE

    # Egasi bekor qilgach, begona uni ko'ra olmaydi
    await harness.press(USER, ItemCallback(action=ItemAction.DO_CANCEL, item_id=1).pack(), with_photo=True)
    hidden = await harness.press(OTHER, ItemCallback(action=ItemAction.VIEW, item_id=1).pack())
    assert hidden[0].text == uz.ITEM_NOT_FOUND


async def test_cancelling_with_photo_card_edits_caption(harness, db):
    await create_lost_wallet(harness)
    done = await harness.press(USER, ItemCallback(action=ItemAction.DO_CANCEL, item_id=1).pack(), with_photo=True)
    assert any(isinstance(m, EditMessageCaption) for m in done)
    assert (await queries.get_item(db, 1)).status is ItemStatus.CANCELLED


async def test_similar_item_notifies_both_owners(harness, db):
    await create_lost_wallet(harness, USER)  # "Qora charm hamyon", Kutubxona, bugun

    # Boshqa talaba o'xshash buyum topadi
    await harness.text(OTHER, uz.BTN_FOUND)
    await harness.text(OTHER, uz.CATEGORIES["bag"])
    await harness.text(OTHER, "Hamyon")
    await harness.text(OTHER, uz.PLACES["library"])
    await harness.text(OTHER, uz.BTN_TODAY)
    await harness.text(OTHER, "Jigarrang, ichida hujjatlar")
    await harness.text(OTHER, uz.BTN_SKIP)
    requests = await harness.text(OTHER, uz.BTN_CONFIRM)

    sent = {m.chat_id: m for m in requests if isinstance(m, SendMessage) and "o'xshash" in m.text}
    assert set(sent) == {USER, OTHER}
    # Har biri qarama-qarshi e'lonni ko'rish tugmasini oladi
    assert sent[OTHER].reply_markup.inline_keyboard[0][0].callback_data == ItemCallback(action=ItemAction.VIEW, item_id=1).pack()
    assert sent[USER].reply_markup.inline_keyboard[0][0].callback_data == ItemCallback(action=ItemAction.VIEW, item_id=2).pack()
    assert keyboard_texts(sent[USER]) == [uz.BTN_VIEW]

    # "Ko'rish" tugmasi e'lonni ochadi
    view = await harness.press(USER, ItemCallback(action=ItemAction.VIEW, item_id=2).pack())
    assert "Hamyon" in view[0].text


async def test_unrelated_item_sends_no_match_notice(harness, db):
    await create_lost_wallet(harness, USER)
    await harness.text(OTHER, uz.BTN_FOUND)
    await harness.text(OTHER, uz.CATEGORIES["book"])
    await harness.text(OTHER, "Fizika darsligi")
    await harness.text(OTHER, uz.PLACES["gym"])
    await harness.text(OTHER, uz.BTN_TODAY)
    await harness.text(OTHER, "Ko'k muqovali")
    await harness.text(OTHER, uz.BTN_SKIP)
    requests = await harness.text(OTHER, uz.BTN_CONFIRM)
    assert not any(isinstance(m, SendMessage) and "o'xshash" in m.text for m in requests)


async def test_app_login_confirmation(harness, db):
    from topdim.handlers.app_login import LoginCallback

    await queries.create_login_code(db, "abc123")
    ask = await harness.text(USER, "/start login_abc123")
    assert last_text(ask) == uz.APP_LOGIN_ASK
    assert keyboard_texts(ask[-1]) == [uz.BTN_APP_LOGIN_CONFIRM]
    # Tasdiqlashdan oldin kod hech kimga bog'lanmagan
    assert (await queries.get_login_code(db, "abc123"))[0] is None

    done = await harness.press(USER, LoginCallback(code="abc123").pack())
    assert last_text(done) == uz.APP_LOGIN_DONE
    assert (await queries.get_login_code(db, "abc123"))[0] == USER

    # Ikkinchi marta (yoki boshqa odam) tasdiqlay olmaydi
    again = await harness.press(OTHER, LoginCallback(code="abc123").pack())
    assert last_text(again) == uz.APP_LOGIN_EXPIRED
    assert (await queries.get_login_code(db, "abc123"))[0] == USER


async def test_app_login_unknown_code(harness):
    requests = await harness.text(USER, "/start login_nomalum")
    assert last_text(requests) == uz.APP_LOGIN_EXPIRED
    # Oddiy /start buzilmagan
    assert "TOPDIM" in last_text(await harness.text(USER, "/start"))
