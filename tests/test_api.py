"""Mobil ilova API'si (topdim/api/server.py) uchun testlar.

aiohttp'ning TestClient'i serverni haqiqiy tarmoqsiz, xotirada ishga tushiradi.
"""

from datetime import timedelta

import pytest
from aiogram import Bot
from aiogram.methods import SendMessage
from aiohttp.test_utils import TestClient, TestServer
from fakes import FAKE_PHOTO_BYTES, FakeSession

from topdim.api.server import create_app
from topdim.db import queries
from topdim.db.models import ItemKind
from topdim.services.dates import today_tashkent

USER, OTHER = 101, 202


@pytest.fixture
async def session():
    return FakeSession()


@pytest.fixture
async def client(db, session):
    bot = Bot("123456:TEST", session=session)
    test_client = TestClient(TestServer(create_app(db, bot, "topdim_test_bot")))
    await test_client.start_server()
    yield test_client
    await test_client.close()


async def login(client: TestClient, db, user_id: int) -> dict[str, str]:
    """To'liq kirish jarayoni: kod → botda tasdiqlash → token."""
    start = await (await client.post("/api/auth/start")).json()
    assert start["url"] == f"https://t.me/topdim_test_bot?start=login_{start['code']}"
    assert await queries.confirm_login_code(db, start["code"], user_id)
    response = await client.post("/api/auth/check", json={"code": start["code"]})
    assert response.status == 200
    token = (await response.json())["token"]
    return {"Authorization": f"Bearer {token}"}


def new_item_payload(**overrides) -> dict:
    payload = {
        "kind": "lost",
        "category": "bag",
        "title": "Qora hamyon",
        "place": "library",
        "event_date": today_tashkent().isoformat(),
        "description": "Ichida talaba guvohnomasi bor",
    }
    payload.update(overrides)
    return payload


async def test_health_and_meta(client):
    assert (await (await client.get("/api/health")).json())["ok"] is True
    meta = await (await client.get("/api/meta")).json()
    assert {"code": "keys", "label": "Kalit"} in meta["categories"]
    assert {"code": "library", "label": "Kutubxona"} in meta["places"]
    assert meta["bot_username"] == "topdim_test_bot"


async def test_unknown_url_returns_readable_json(client):
    response = await client.get("/api/health/api/health")
    assert response.status == 404
    assert "192.168.1.5:8080" in (await response.json())["error"]


async def test_login_flow(client, db):
    start = await (await client.post("/api/auth/start")).json()
    pending = await client.post("/api/auth/check", json={"code": start["code"]})
    assert pending.status == 202

    headers = await login(client, db, USER)
    assert (await client.get("/api/my/items", headers=headers)).status == 200
    await client.post("/api/auth/logout", headers=headers)
    assert (await client.get("/api/my/items", headers=headers)).status == 401


async def test_used_and_expired_codes(client, db):
    start = await (await client.post("/api/auth/start")).json()
    await queries.confirm_login_code(db, start["code"], USER)
    assert (await client.post("/api/auth/check", json={"code": start["code"]})).status == 200
    assert (await client.post("/api/auth/check", json={"code": start["code"]})).status == 410
    assert (await client.post("/api/auth/check", json={"code": "yoq-kod"})).status == 410


async def test_protected_endpoints_require_token(client):
    assert (await client.get("/api/my/items")).status == 401
    assert (await client.post("/api/items", json=new_item_payload())).status == 401
    bad = await client.get("/api/my/items", headers={"Authorization": "Bearer soxta"})
    assert bad.status == 401
    assert "kiring" in (await bad.json())["error"]


async def test_create_search_and_view_item(client, db):
    headers = await login(client, db, USER)
    created = await client.post("/api/items", json=new_item_payload(), headers=headers)
    assert created.status == 201
    item = await created.json()
    assert item["is_mine"] is True and item["category_label"] == "Sumka/hamyon"
    assert "owner_id" not in item  # egasi hech qachon oshkor bo'lmaydi

    found = await (await client.get("/api/items", params={"q": "hamyon"})).json()
    assert found["total"] == 1 and found["items"][0]["is_mine"] is False
    assert (await (await client.get("/api/items", params={"q": "velosiped"})).json())["total"] == 0
    assert (await (await client.get("/api/items", params={"category": "keys"})).json())["total"] == 0

    view = await (await client.get(f"/api/items/{item['id']}")).json()
    assert view["title"] == "Qora hamyon" and view["place_label"] == "Kutubxona"
    assert (await client.get("/api/items/999")).status == 404


@pytest.mark.parametrize(
    ("overrides", "error_part"),
    [
        ({"kind": "boshqa"}, "Turi"),
        ({"category": "car"}, "Kategoriya"),
        ({"title": ""}, "Nomi"),
        ({"description": "Tel: +998 90 123 45 67"}, "telefon"),
        ({"place": "other"}, "joyni yozing"),
        ({"event_date": "2020-01-01"}, "eski"),
        ({"event_date": (today_tashkent() + timedelta(days=2)).isoformat()}, "kelmagan"),
        ({"event_date": "kecha"}, "noto'g'ri"),
    ],
)
async def test_create_item_validation(client, db, overrides, error_part):
    headers = await login(client, db, USER)
    response = await client.post("/api/items", json=new_item_payload(**overrides), headers=headers)
    assert response.status == 400
    assert error_part in (await response.json())["error"]


async def test_other_place_with_note(client, db):
    headers = await login(client, db, USER)
    payload = new_item_payload(place="other", place_note="Avtobus bekati")
    item = await (await client.post("/api/items", json=payload, headers=headers)).json()
    assert item["place_label"] == "Avtobus bekati"


async def test_status_change_only_by_owner(client, db):
    owner = await login(client, db, USER)
    stranger = await login(client, db, OTHER)
    item = await (await client.post("/api/items", json=new_item_payload(), headers=owner)).json()
    url = f"/api/items/{item['id']}/status"

    assert (await client.post(url, json={"status": "returned"}, headers=stranger)).status == 403
    assert (await client.post(url, json={"status": "active"}, headers=owner)).status == 400
    done = await client.post(url, json={"status": "returned"}, headers=owner)
    assert (await done.json())["status"] == "returned"
    assert (await client.post(url, json={"status": "cancelled"}, headers=owner)).status == 409

    # Yopilgan e'lon qidiruvda yo'q, begonaga ko'rinmaydi, egasiga ko'rinadi
    assert (await (await client.get("/api/items")).json())["total"] == 0
    assert (await client.get(f"/api/items/{item['id']}", headers=stranger)).status == 404
    assert (await client.get(f"/api/items/{item['id']}", headers=owner)).status == 200
    mine = await (await client.get("/api/my/items", headers=owner)).json()
    assert mine["items"][0]["status"] == "returned"


async def test_app_item_triggers_telegram_match_notice(client, db, session):
    # Botda berilgan "topilgan" e'lon
    await queries.create_item(db, queries.NewItem(
        kind=ItemKind.FOUND, owner_id=OTHER, category="bag", title="Hamyon", place="library",
        place_note=None, event_date=today_tashkent(), description="Jigarrang", photo_file_id=None,
    ))
    headers = await login(client, db, USER)
    await client.post("/api/items", json=new_item_payload(), headers=headers)

    notices = [m for m in session.requests if isinstance(m, SendMessage) and "o'xshash" in m.text]
    assert {m.chat_id for m in notices} == {USER, OTHER}


async def test_item_photo_is_proxied_from_telegram(client, db):
    item_id = await queries.create_item(db, queries.NewItem(
        kind=ItemKind.FOUND, owner_id=OTHER, category="keys", title="Kalit", place="gym",
        place_note=None, event_date=today_tashkent(), description="Qizil brelok", photo_file_id="tg-file",
    ))
    item = await (await client.get(f"/api/items/{item_id}")).json()
    assert item["has_photo"] is True
    photo = await client.get(f"/api/items/{item_id}/photo")
    assert photo.status == 200 and photo.content_type == "image/jpeg"
    assert await photo.read() == FAKE_PHOTO_BYTES
