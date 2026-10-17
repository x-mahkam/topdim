"""Ma'lumotlar bazasi bilan ishlovchi yupqa qatlam.

Butun loyiha bazaga faqat shu klassdagi uchta metod orqali murojaat qiladi:
``execute``, ``fetch_one`` va ``fetch_all``. Shuning uchun keyinchalik
PostgreSQL'ga o'tishda (masalan, asyncpg bilan) asosan shu fayl va
db/queries.py'dagi SQL so'rovlar o'zgaradi, handlerlar esa o'zgarmaydi.
"""

from typing import Any, Sequence

import aiosqlite

# Jadval tuzilmasi. "IF NOT EXISTS" tufayli bot har ishga tushganda
# xavfsiz bajariladi: jadval bo'lsa, tegmaydi.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,   -- Telegram user_id
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    kind           TEXT NOT NULL CHECK (kind IN ('lost', 'found')),
    owner_id       INTEGER NOT NULL REFERENCES users(user_id),
    category       TEXT NOT NULL,
    title          TEXT NOT NULL,
    place          TEXT NOT NULL,
    place_note     TEXT,
    event_date     TEXT NOT NULL,          -- YYYY-MM-DD
    description    TEXT NOT NULL,
    photo_file_id  TEXT,
    search_text    TEXT NOT NULL,          -- qidiruv uchun normallashtirilgan matn
    status         TEXT NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active', 'returned', 'cancelled')),
    created_at     TEXT NOT NULL,          -- ISO formatdagi UTC vaqt
    updated_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner_id);
CREATE INDEX IF NOT EXISTS idx_items_status_kind ON items(status, kind);
"""

Params = Sequence[Any]


class Database:
    """SQLite bazaga ulanish."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Bazaga ulanadi va jadvallarni yaratadi."""
        self._conn = await aiosqlite.connect(self.path)
        # Qatorlarga ustun nomi bilan murojaat qilish uchun: row["title"]
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Bazaga ulanilmagan. Avval connect() chaqiring.")
        return self._conn

    async def execute(self, sql: str, params: Params = ()) -> int:
        """O'zgartiruvchi so'rov (INSERT/UPDATE).

        INSERT uchun yangi qator ID'sini, UPDATE uchun o'zgargan qatorlar sonini
        qaytaradi.
        """
        cursor = await self.conn.execute(sql, params)
        await self.conn.commit()
        if sql.lstrip().upper().startswith("INSERT"):
            return cursor.lastrowid or 0
        return cursor.rowcount

    async def fetch_one(self, sql: str, params: Params = ()) -> aiosqlite.Row | None:
        """Bitta qatorni qaytaradi (yoki None)."""
        async with self.conn.execute(sql, params) as cursor:
            return await cursor.fetchone()

    async def fetch_all(self, sql: str, params: Params = ()) -> list[aiosqlite.Row]:
        """Barcha qatorlarni ro'yxat ko'rinishida qaytaradi."""
        async with self.conn.execute(sql, params) as cursor:
            return list(await cursor.fetchall())
