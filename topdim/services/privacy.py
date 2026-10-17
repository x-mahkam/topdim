"""Shaxsiy ma'lumotlarni himoyalash.

Bot telefon raqamini so'ramaydi. Lekin foydalanuvchi uni tavsifga o'zi yozib
qo'yishi mumkin — bu funksiya shunday holatlarni aniqlaydi.
"""

import re

# Kamida 9 ta raqam, orasida bo'shliq, tire, nuqta yoki qavs bo'lishi mumkin.
# Masalan: +998 90 123-45-67, 901234567, 8600 1234 5678 9012 (karta raqami).
_PHONE_LIKE_RE = re.compile(r"\+?\d(?:[\s\-.()]*\d){8,}")


def contains_phone_number(text: str) -> bool:
    """Matnda telefon yoki karta raqamiga o'xshash ketma-ketlik bormi?"""
    return bool(_PHONE_LIKE_RE.search(text))
