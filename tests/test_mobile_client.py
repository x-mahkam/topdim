"""Mobil ilovaning HTTP mijozi (mobile/src/api_client.py) uchun testlar.

Mijoz haqiqiy TCP orqali ishlaydi, shuning uchun API server shu yerning
o'zida, tasodifiy portda ishga tushiriladi.
"""

import sys
from pathlib import Path

import pytest
from aiogram import Bot
from aiohttp.test_utils import TestServer
from fakes import FakeSession

from topdim.api.server import create_app
from topdim.db import queries
from topdim.services.dates import today_tashkent

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mobile" / "src"))
from api_client import ApiError, TopdimApi, normalize_server_url  # noqa: E402


@pytest.fixture
async def server(db):
    bot = Bot("123456:TEST", session=FakeSession())
    test_server = TestServer(create_app(db, bot, "topdim_test_bot"), host="127.0.0.1")
    await test_server.start_server()
    yield f"127.0.0.1:{test_server.port}"
    await test_server.close()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("192.168.1.5:8080", "http://192.168.1.5:8080"),
        (" https://topdim.uz/ ", "https://topdim.uz"),
        ("192.168.1.5:8080/api/health", "http://192.168.1.5:8080"),
        ("http://192.168.1.5:8080/api/health/", "http://192.168.1.5:8080"),
        ("", ""),
    ],
)
def test_normalize_server_url(text, expected):
    assert normalize_server_url(text) == expected


async def test_full_flow_through_client(server, db):
    api = TopdimApi(server)
    assert (await api.health())["bot"] == "topdim_test_bot"
    assert any(c["code"] == "keys" for c in (await api.meta())["categories"])

    # Kirish: tasdiqlanmaguncha None, tasdiqlangach token
    start = await api.auth_start()
    assert await api.auth_check(start["code"]) is None
    await queries.confirm_login_code(db, start["code"], 101)
    api.token = await api.auth_check(start["code"])
    assert api.token

    item = await api.create_item({
        "kind": "found", "category": "keys", "title": "Kalitlar", "place": "gym",
        "event_date": today_tashkent().isoformat(), "description": "Qizil brelok bilan",
    })
    assert item["is_mine"] is True

    found = await api.items("kalit")
    assert found["total"] == 1 and (await api.item(item["id"]))["title"] == "Kalitlar"
    assert (await api.my_items())["total"] == 1

    assert (await api.set_status(item["id"], "returned"))["status"] == "returned"
    assert (await api.items())["total"] == 0


async def test_server_errors_are_readable(server, db):
    api = TopdimApi(server)
    with pytest.raises(ApiError) as error:
        await api.my_items()
    assert error.value.status == 401 and "kiring" in error.value.message

    with pytest.raises(ApiError) as error:
        await api.item(999)
    assert error.value.status == 404


async def test_unreachable_server():
    api = TopdimApi("127.0.0.1:9")  # bu portda server yo'q
    with pytest.raises(ApiError) as error:
        await api.health()
    assert "Serverga ulanib bo'lmadi" in error.value.message
