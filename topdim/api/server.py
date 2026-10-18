"""Mobil ilova uchun HTTP API (JSON).

Server bot bilan bitta jarayonda ishlaydi va o'sha bazadan foydalanadi:
ilovada berilgan e'lon botdagi qidiruvda ham chiqadi, o'xshash e'lon
topilsa xabar Telegram orqali keladi.

Manzillar:
    GET  /api/health                 — server ishlayaptimi
    GET  /api/meta                   — kategoriyalar va joylar ro'yxati
    POST /api/auth/start             — kirish kodi va Telegram havolasi
    POST /api/auth/check             — kod tasdiqlandimi → token
    POST /api/auth/logout            — chiqish                      🔒
    GET  /api/items?q=&category=&page=  — faol e'lonlar qidiruvi
    GET  /api/items/{id}             — bitta e'lon
    GET  /api/items/{id}/photo       — e'lon rasmi (JPEG)
    POST /api/items                  — yangi e'lon                  🔒
    GET  /api/my/items?page=         — mening e'lonlarim            🔒
    POST /api/items/{id}/status      — "returned" yoki "cancelled"  🔒

🔒 — ``Authorization: Bearer <token>`` sarlavhasi talab qilinadi.
E'lon egasi haqidagi ma'lumot (Telegram ID) hech qachon qaytarilmaydi.
"""

import logging
from datetime import date, datetime, timezone
from typing import Any

from aiogram import Bot
from aiohttp import web

from topdim.db import queries
from topdim.db.database import Database
from topdim.db.models import Item, ItemKind, ItemStatus
from topdim.locales import uz
from topdim.services import auth
from topdim.services.dates import DateInputError, MAX_AGE_DAYS, format_date, parse_user_date, today_tashkent
from topdim.services.notifications import notify_matches
from topdim.services.pagination import make_page
from topdim.services.text import extract_keywords
from topdim.services.validation import (
    DESCRIPTION_MAX,
    DESCRIPTION_MIN,
    PLACE_MAX,
    PLACE_MIN,
    TITLE_MAX,
    TITLE_MIN,
    validate_text,
)

logger = logging.getLogger(__name__)

# Ilovaga bitta sahifada shuncha e'lon yuboriladi
API_PER_PAGE = 20

# Ilova ichida ishlatiladigan obyektlar (aiohttp'ning "AppKey" mexanizmi)
DB_KEY = web.AppKey("db", Database)
BOT_KEY = web.AppKey("bot", Bot)
BOT_USERNAME_KEY = web.AppKey("bot_username", str)


class ApiError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato. Javob: {"error": "..."}."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@web.middleware
async def error_middleware(request: web.Request, handler):
    """ApiError'ni chiroyli JSON javobga aylantiradi."""
    try:
        return await handler(request)
    except ApiError as error:
        return web.json_response({"error": error.message}, status=error.status)
    except web.HTTPNotFound:
        return web.json_response({"error": uz.API_NOT_FOUND}, status=404)


# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------
def strip_emoji(label: str) -> str:
    """"🔑 Kalit" -> "Kalit": ilovada belgilarni o'zimiz chizamiz."""
    first, _, rest = label.partition(" ")
    return rest if rest and not first.isalnum() else label


def item_to_json(item: Item, viewer_id: int | None) -> dict[str, Any]:
    """E'lonni JSON'ga aylantiradi. Egasining ID'si qo'shilmaydi!"""
    place = item.place_note or strip_emoji(uz.PLACES.get(item.place, item.place))
    return {
        "id": item.id,
        "kind": item.kind.value,
        "category": item.category,
        "category_label": strip_emoji(uz.CATEGORIES.get(item.category, item.category)),
        "title": item.title,
        "place": item.place,
        "place_label": place,
        "event_date": item.event_date.isoformat(),
        "event_date_label": format_date(item.event_date),
        "description": item.description,
        "status": item.status.value,
        "has_photo": item.photo_file_id is not None,
        "is_mine": viewer_id is not None and viewer_id == item.owner_id,
    }


def page_number(request: web.Request) -> int:
    """?page=2 -> 1 (ichkarida sahifalar 0 dan boshlanadi)."""
    try:
        return max(int(request.query.get("page", "1")) - 1, 0)
    except ValueError:
        return 0


def item_id_from(request: web.Request) -> int:
    try:
        return int(request.match_info["item_id"])
    except ValueError:
        raise ApiError(uz.ITEM_NOT_FOUND, 404) from None


async def read_json(request: web.Request) -> dict[str, Any]:
    try:
        data = await request.json()
    except ValueError:
        raise ApiError(uz.API_BAD_REQUEST) from None
    if not isinstance(data, dict):
        raise ApiError(uz.API_BAD_REQUEST)
    return data


async def current_user(request: web.Request, required: bool = True) -> int | None:
    """Token bo'yicha foydalanuvchini aniqlaydi."""
    header = request.headers.get("Authorization", "")
    token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
    user_id = None
    if token:
        user_id = await queries.get_session_user(request.app[DB_KEY], auth.hash_token(token))
    if user_id is None and required:
        raise ApiError(uz.API_LOGIN_REQUIRED, 401)
    return user_id


def paginated(items: list[Item], page, viewer_id: int | None) -> dict[str, Any]:
    return {
        "items": [item_to_json(item, viewer_id) for item in items],
        "page": page.number + 1,
        "total_pages": page.total_pages,
        "total": page.total_items,
    }


# ---------------------------------------------------------------------------
# Umumiy ma'lumotlar
# ---------------------------------------------------------------------------
async def health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "bot": request.app[BOT_USERNAME_KEY]})


async def meta(request: web.Request) -> web.Response:
    """Kategoriya va joylar: ilova ularni o'zida saqlamaydi, serverdan oladi."""
    def as_list(mapping: dict[str, str]) -> list[dict[str, str]]:
        return [{"code": code, "label": strip_emoji(label)} for code, label in mapping.items()]

    return web.json_response({
        "categories": as_list(uz.CATEGORIES),
        "places": as_list(uz.PLACES),
        "bot_username": request.app[BOT_USERNAME_KEY],
    })


# ---------------------------------------------------------------------------
# Kirish (Telegram orqali)
# ---------------------------------------------------------------------------
async def auth_start(request: web.Request) -> web.Response:
    code = auth.new_login_code()
    await queries.create_login_code(request.app[DB_KEY], code)
    return web.json_response({
        "code": code,
        "url": auth.login_deep_link(request.app[BOT_USERNAME_KEY], code),
        "expires_in": int(auth.LOGIN_CODE_TTL.total_seconds()),
    })


async def auth_check(request: web.Request) -> web.Response:
    """Ilova shu manzilni har 2-3 soniyada so'rab turadi.

    202 — hali tasdiqlanmagan, 200 — token tayyor, 410 — kod eskirgan.
    """
    db = request.app[DB_KEY]
    code = str((await read_json(request)).get("code", ""))
    found = await queries.get_login_code(db, code)
    if found is None:
        raise ApiError(uz.APP_LOGIN_EXPIRED, 410)
    user_id, created_at = found
    if auth.is_code_expired(created_at, datetime.now(timezone.utc)):
        await queries.delete_login_code(db, code)
        raise ApiError(uz.APP_LOGIN_EXPIRED, 410)
    if user_id is None:
        return web.json_response({"status": "pending"}, status=202)

    # Avval sessiya yaratiladi, keyin kod o'chiriladi (kod bir martalik)
    token = auth.new_session_token()
    await queries.create_session(db, auth.hash_token(token), user_id)
    await queries.delete_login_code(db, code)
    return web.json_response({"status": "ok", "token": token})


async def auth_logout(request: web.Request) -> web.Response:
    await current_user(request)
    token = request.headers["Authorization"].removeprefix("Bearer ").strip()
    await queries.delete_session(request.app[DB_KEY], auth.hash_token(token))
    return web.json_response({"ok": True})


# ---------------------------------------------------------------------------
# E'lonlar
# ---------------------------------------------------------------------------
async def list_items(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    viewer = await current_user(request, required=False)
    keywords = extract_keywords(request.query.get("q", "")[:60])
    category = request.query.get("category") or None
    if category is not None and category not in uz.CATEGORIES:
        category = None

    total = await queries.count_search_items(db, keywords, category)
    page = make_page(total, page_number(request), per_page=API_PER_PAGE)
    items = await queries.search_items(db, keywords, category, limit=page.per_page, offset=page.offset)
    return web.json_response(paginated(items, page, viewer))


async def load_visible_item(request: web.Request) -> tuple[Item, int | None]:
    """E'lonni qaytaradi: faol bo'lsa hammaga, yopilgan bo'lsa faqat egasiga."""
    viewer = await current_user(request, required=False)
    item = await queries.get_item(request.app[DB_KEY], item_id_from(request))
    if item is None or (item.status is not ItemStatus.ACTIVE and item.owner_id != viewer):
        raise ApiError(uz.ITEM_NOT_FOUND, 404)
    return item, viewer


async def get_item(request: web.Request) -> web.Response:
    item, viewer = await load_visible_item(request)
    return web.json_response(item_to_json(item, viewer))


async def item_photo(request: web.Request) -> web.Response:
    """Rasm Telegram serverlarida saqlanadi; server uni bot orqali olib beradi."""
    item, _ = await load_visible_item(request)
    if item.photo_file_id is None:
        raise ApiError(uz.ITEM_NOT_FOUND, 404)
    data = await request.app[BOT_KEY].download(item.photo_file_id)
    return web.Response(
        body=data.read(),
        content_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


def required_text(data: dict[str, Any], field: str, label: str, min_len: int, max_len: int) -> str:
    value = str(data.get(field) or "").strip()
    if not value:
        raise ApiError(uz.API_FIELD_REQUIRED.format(field=label))
    error = validate_text(value, min_len, max_len)
    if error:
        raise ApiError(f"{label}: {error}")
    return value


def parse_new_item(data: dict[str, Any], owner_id: int, today: date) -> queries.NewItem:
    """Ilovadan kelgan ma'lumotni tekshirib, NewItem'ga aylantiradi.

    Botdagi qoidalar bilan bir xil: uzunlik, telefon raqami, sana.
    """
    try:
        kind = ItemKind(data.get("kind"))
    except ValueError:
        raise ApiError(uz.API_UNKNOWN_CHOICE.format(field="Turi")) from None

    category = data.get("category")
    if category not in uz.CATEGORIES:
        raise ApiError(uz.API_UNKNOWN_CHOICE.format(field="Kategoriya"))
    place = data.get("place")
    if place not in uz.PLACES:
        raise ApiError(uz.API_UNKNOWN_CHOICE.format(field="Joy"))

    title = required_text(data, "title", "Nomi", TITLE_MIN, TITLE_MAX)
    description = required_text(data, "description", "Tavsif", DESCRIPTION_MIN, DESCRIPTION_MAX)
    place_note = None
    if place == "other":
        if not str(data.get("place_note") or "").strip():
            raise ApiError(uz.API_PLACE_NOTE_REQUIRED)
        place_note = required_text(data, "place_note", "Joy", PLACE_MIN, PLACE_MAX)

    try:
        event_date = date.fromisoformat(str(data.get("event_date")))
        # Bot bilan bir xil tekshiruv: kelajak va juda eski sanalar qabul qilinmaydi
        parse_user_date(format_date(event_date), today)
    except ValueError as error:
        reason = error.reason if isinstance(error, DateInputError) else "format"
        texts = {
            "format": uz.DATE_BAD_FORMAT,
            "future": uz.DATE_IN_FUTURE,
            "too_old": uz.DATE_TOO_OLD.format(days=MAX_AGE_DAYS),
        }
        raise ApiError(texts[reason].replace("<b>", "").replace("</b>", "")) from None

    return queries.NewItem(
        kind=kind,
        owner_id=owner_id,
        category=category,
        title=title,
        place=place,
        place_note=place_note,
        event_date=event_date,
        description=description,
        photo_file_id=None,
    )


async def create_item(request: web.Request) -> web.Response:
    db, bot = request.app[DB_KEY], request.app[BOT_KEY]
    user_id = await current_user(request)
    new_item = parse_new_item(await read_json(request), user_id, today_tashkent())
    item_id = await queries.create_item(db, new_item)

    # O'xshash e'lonlar haqida xabar Telegram orqali boradi (2-bosqich)
    try:
        await notify_matches(bot, db, await queries.get_item(db, item_id))
    except Exception:
        logger.exception("E'lon #%s uchun moslashtirishda xato", item_id)

    item = await queries.get_item(db, item_id)
    return web.json_response(item_to_json(item, user_id), status=201)


async def my_items(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    user_id = await current_user(request)
    total = await queries.count_user_items(db, user_id)
    page = make_page(total, page_number(request), per_page=API_PER_PAGE)
    items = await queries.list_user_items(db, user_id, limit=page.per_page, offset=page.offset)
    return web.json_response(paginated(items, page, user_id))


async def change_status(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    user_id = await current_user(request)
    try:
        new_status = ItemStatus(str((await read_json(request)).get("status")))
    except ValueError:
        raise ApiError(uz.API_UNKNOWN_CHOICE.format(field="Holat")) from None
    if new_status is ItemStatus.ACTIVE:
        raise ApiError(uz.API_UNKNOWN_CHOICE.format(field="Holat"))

    item = await queries.get_item(db, item_id_from(request))
    if item is None:
        raise ApiError(uz.ITEM_NOT_FOUND, 404)
    if item.owner_id != user_id:
        raise ApiError(uz.ITEM_NOT_YOURS, 403)
    if not await queries.close_item(db, item.id, user_id, new_status):
        raise ApiError(uz.ITEM_NOT_ACTIVE, 409)
    return web.json_response(item_to_json(await queries.get_item(db, item.id), user_id))


# ---------------------------------------------------------------------------
# Ilovani yig'ish va ishga tushirish
# ---------------------------------------------------------------------------
def create_app(db: Database, bot: Bot, bot_username: str) -> web.Application:
    app = web.Application(middlewares=[error_middleware], client_max_size=64 * 1024)
    app[DB_KEY] = db
    app[BOT_KEY] = bot
    app[BOT_USERNAME_KEY] = bot_username
    app.add_routes([
        web.get("/api/health", health),
        web.get("/api/meta", meta),
        web.post("/api/auth/start", auth_start),
        web.post("/api/auth/check", auth_check),
        web.post("/api/auth/logout", auth_logout),
        web.get("/api/items", list_items),
        web.post("/api/items", create_item),
        web.get(r"/api/items/{item_id}", get_item),
        web.get(r"/api/items/{item_id}/photo", item_photo),
        web.post(r"/api/items/{item_id}/status", change_status),
        web.get("/api/my/items", my_items),
    ])
    return app


async def start_api(app: web.Application, host: str, port: int) -> web.AppRunner:
    """Serverni fonda ishga tushiradi. To'xtatish: ``await runner.cleanup()``."""
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    logger.info("API ishga tushdi: http://%s:%s/api/health", host, port)
    return runner
