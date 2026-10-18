"""Bot sozlamalarini .env faylidan o'qish.

.env fayl maxfiy ma'lumotlarni (masalan, bot tokenini) koddan ajratib turadi.
U git'ga qo'shilmaydi, namunasi esa .env.example faylida.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    """Sozlamalarda xato bo'lsa ko'tariladi."""


@dataclass(frozen=True)
class Config:
    """Botning barcha sozlamalari bitta joyda."""

    bot_token: str
    admin_ids: frozenset[int]
    db_path: str
    # Mobil ilova uchun API server. Port 0 bo'lsa server ishga tushmaydi.
    api_host: str = "0.0.0.0"
    api_port: int = 8080


def parse_admin_ids(raw: str) -> frozenset[int]:
    """"123, 456" ko'rinishidagi satrni ID'lar to'plamiga aylantiradi.

    Bo'sh satr — adminlar yo'q degani. Raqam bo'lmagan qiymat xato hisoblanadi.
    """
    ids = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if not part.lstrip("-").isdigit():
            raise ConfigError(f"ADMIN_IDS ichida noto'g'ri qiymat: {part!r}")
        ids.add(int(part))
    return frozenset(ids)


def load_config(env_file: str | None = ".env") -> Config:
    """Sozlamalarni o'qiydi: avval .env fayldan, keyin muhit o'zgaruvchilaridan."""
    if env_file:
        load_dotenv(env_file)

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError(
            "BOT_TOKEN topilmadi. .env.example faylidan nusxa olib, .env yarating "
            "va unga @BotFather bergan tokenni yozing."
        )

    api_port = os.getenv("API_PORT", "8080").strip() or "0"
    if not api_port.isdigit():
        raise ConfigError(f"API_PORT raqam bo'lishi kerak: {api_port!r}")

    return Config(
        bot_token=token,
        admin_ids=parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        db_path=os.getenv("DB_PATH", "topdim.db").strip() or "topdim.db",
        api_host=os.getenv("API_HOST", "0.0.0.0").strip() or "0.0.0.0",
        api_port=int(api_port),
    )
