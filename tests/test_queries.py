"""db/queries.py uchun testlar (vaqtinchalik SQLite bazada)."""

from datetime import date

from topdim.db import queries
from topdim.db.models import ItemKind, ItemStatus


def new_item(**overrides) -> queries.NewItem:
    values = dict(
        kind=ItemKind.LOST,
        owner_id=1,
        category="bag",
        title="Qora hamyon",
        place="library",
        place_note=None,
        event_date=date(2026, 10, 10),
        description="Ichida talaba guvohnomasi bor",
        photo_file_id=None,
    )
    values.update(overrides)
    return queries.NewItem(**values)


async def test_create_and_get_item(db):
    item_id = await queries.create_item(db, new_item())
    item = await queries.get_item(db, item_id)
    assert item.title == "Qora hamyon"
    assert item.status is ItemStatus.ACTIVE
    assert item.event_date == date(2026, 10, 10)
    assert await queries.get_item(db, 999) is None


async def test_search_by_keyword_and_category(db):
    await queries.create_item(db, new_item(title="Qora hamyon"))
    await queries.create_item(db, new_item(title="Ko'k sumka", description="Oʻquv qurollari"))
    await queries.create_item(db, new_item(title="Uy kaliti", category="keys", description="Brelok bilan"))

    assert await queries.count_search_items(db, ["hamyon"], None) == 1
    # Tutuq belgisi har xil yozilsa ham topiladi
    assert await queries.count_search_items(db, ["o'quv"], None) == 1
    assert await queries.count_search_items(db, [], "bag") == 2
    assert await queries.count_search_items(db, ["kaliti"], "bag") == 0
    # Barcha kalit so'zlar mos kelishi kerak
    assert await queries.count_search_items(db, ["qora", "sumka"], None) == 0


async def test_search_escapes_like_wildcards(db):
    await queries.create_item(db, new_item(title="Hamyon"))
    assert await queries.count_search_items(db, ["%"], None) == 0
    assert await queries.count_search_items(db, ["_"], None) == 0


async def test_search_pagination_newest_first(db):
    ids = [await queries.create_item(db, new_item(title=f"Kitob {n}", category="book")) for n in range(7)]
    first = await queries.search_items(db, [], "book", limit=5, offset=0)
    second = await queries.search_items(db, [], "book", limit=5, offset=5)
    assert [i.id for i in first] == ids[::-1][:5]
    assert [i.id for i in second] == ids[::-1][5:]


async def test_closed_items_are_hidden_from_search(db):
    item_id = await queries.create_item(db, new_item())
    assert await queries.close_item(db, item_id, owner_id=1, new_status=ItemStatus.RETURNED)
    assert await queries.count_search_items(db, [], None) == 0
    # Lekin egasining ro'yxatida qoladi
    assert await queries.count_user_items(db, 1) == 1


async def test_only_owner_can_close_active_item(db):
    item_id = await queries.create_item(db, new_item(owner_id=1))
    assert not await queries.close_item(db, item_id, owner_id=2, new_status=ItemStatus.CANCELLED)
    assert await queries.close_item(db, item_id, owner_id=1, new_status=ItemStatus.CANCELLED)
    # Yopilgan e'lonni qayta yopib bo'lmaydi
    assert not await queries.close_item(db, item_id, owner_id=1, new_status=ItemStatus.RETURNED)
    assert (await queries.get_item(db, item_id)).status is ItemStatus.CANCELLED


async def test_user_items_active_first(db):
    old = await queries.create_item(db, new_item(title="Eski"))
    await queries.close_item(db, old, owner_id=1, new_status=ItemStatus.RETURNED)
    fresh = await queries.create_item(db, new_item(title="Yangi"))
    await queries.create_item(db, new_item(owner_id=2, title="Begona"))

    items = await queries.list_user_items(db, 1, limit=5, offset=0)
    assert [i.id for i in items] == [fresh, old]
