"""Foydalanuvchilarga bot tashabbusi bilan xabar yuborish.

Bu yerda moslashtirish bosqichlari birlashtiriladi:
    1. bazadan nomzod e'lonlarni olish (db/queries.py);
    2. ballarni hisoblash (services/matching.py);
    3. yangi juftliklarni saqlash va ikkala egaga xabar yuborish.
"""

import logging
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from topdim.db import queries
from topdim.db.database import Database
from topdim.db.models import Item
from topdim.keyboards import inline
from topdim.locales import uz
from topdim.services.matching import MAX_DAYS_APART, MatchResult, find_matches

logger = logging.getLogger(__name__)


async def safe_send(bot: Bot, user_id: int, text: str, markup: InlineKeyboardMarkup | None = None) -> bool:
    """Xabar yuboradi. Foydalanuvchi botni bloklagan bo'lsa ham bot to'xtamaydi."""
    try:
        await bot.send_message(user_id, text, reply_markup=markup)
        return True
    except TelegramAPIError as error:
        logger.warning("Foydalanuvchi %s ga xabar yuborilmadi: %s", user_id, error)
        return False


async def notify_matches(bot: Bot, db: Database, item: Item) -> list[MatchResult]:
    """Yangi e'longa o'xshashlarini topib, ikkala tomonga xabar yuboradi.

    Faqat yangi juftliklar haqida xabar beriladi. Topilgan juftliklar ro'yxati
    qaytariladi (testlar va log uchun qulay).
    """
    candidates = await queries.list_match_candidates(db, item, MAX_DAYS_APART)
    matches = find_matches(item, candidates)

    new_matches = [match for match in matches if await queries.save_match(db, item, match.item, match.score)]
    if not new_matches:
        return []

    # 1) Yangi e'lon egasiga — bitta xabar, har bir o'xshash e'lon uchun tugma
    await safe_send(
        bot,
        item.owner_id,
        uz.MATCH_FOUND_FOR_NEW.format(
            own_id=item.id, own_title=escape(item.title, quote=False), count=len(new_matches)
        ),
        inline.view_items([match.item.id for match in new_matches]),
    )

    # 2) Har bir eski e'lon egasiga — yangi e'lonni ko'rish tugmasi bilan
    for match in new_matches:
        other = match.item
        await safe_send(
            bot,
            other.owner_id,
            uz.MATCH_FOUND_FOR_EXISTING.format(
                own_id=other.id,
                own_title=escape(other.title, quote=False),
                other_id=item.id,
                other_title=escape(item.title, quote=False),
            ),
            inline.view_items([item.id]),
        )

    logger.info("E'lon #%s uchun %s ta o'xshash e'lon topildi", item.id, len(new_matches))
    return new_matches
