"""Mobil ilovaga kirish uchun kodlar va tokenlar.

Kirish jarayoni (telefon raqami kerak emas):
    1. Ilova serverdan bir martalik kod oladi.
    2. Foydalanuvchi t.me/<bot>?start=login_<kod> havolasini ochadi.
    3. Bot "Ilovaga kirishni tasdiqlaysizmi?" deb so'raydi.
    4. Tasdiqlangach, ilova shu kod evaziga doimiy token oladi.

Kodlar va tokenlar ``secrets`` moduli bilan yaratiladi — ularni taxmin qilib
bo'lmaydi. Bazada tokenning o'zi emas, faqat uning SHA-256 xeshi saqlanadi:
baza fayli boshqa birov qo'liga tushsa ham, tokenlar oshkor bo'lmaydi.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

LOGIN_PREFIX = "login_"
LOGIN_CODE_TTL = timedelta(minutes=10)  # kod shuncha vaqt amal qiladi


def new_login_code() -> str:
    """22 belgili tasodifiy kod (Telegram deep-link'ga mos: A-Z, a-z, 0-9, _ -)."""
    return secrets.token_urlsafe(16)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login_deep_link(bot_username: str, code: str) -> str:
    return f"https://t.me/{bot_username}?start={LOGIN_PREFIX}{code}"


def is_code_expired(created_at: datetime, now: datetime) -> bool:
    return now - created_at > LOGIN_CODE_TTL
