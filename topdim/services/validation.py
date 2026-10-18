"""Foydalanuvchi kiritgan matnlarni tekshirish.

Bu qoidalar ham Telegram bot, ham mobil ilova API'si uchun umumiy: shunda
ikkala joyda ham bir xil cheklovlar ishlaydi.
"""

from topdim.locales import uz
from topdim.services.privacy import contains_phone_number

# Matn uzunligi chegaralari
TITLE_MIN, TITLE_MAX = 2, 100
PLACE_MIN, PLACE_MAX = 2, 100
DESCRIPTION_MIN, DESCRIPTION_MAX = 5, 700  # rasm izohi 1024 belgidan oshmasligi kerak


def validate_text(text: str, min_len: int, max_len: int) -> str | None:
    """Foydalanuvchi matnini tekshiradi.

    Hammasi joyida bo'lsa None, aks holda foydalanuvchiga ko'rsatiladigan
    xato matnini qaytaradi.
    """
    if len(text) < min_len:
        return uz.TEXT_TOO_SHORT.format(min=min_len)
    if len(text) > max_len:
        return uz.TEXT_TOO_LONG.format(max=max_len, length=len(text))
    if contains_phone_number(text):
        return uz.CONTAINS_PHONE
    return None
