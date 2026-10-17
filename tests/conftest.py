"""Testlar uchun umumiy fixture'lar."""

import pytest

from topdim.db.database import Database


@pytest.fixture
async def db(tmp_path):
    """Har bir test uchun alohida, toza SQLite baza."""
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()
