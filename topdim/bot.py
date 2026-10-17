"""TOPDIM botini ishga tushirish nuqtasi.

Ishga tushirish (loyiha ildiz papkasidan):
    python -m topdim.bot
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from topdim.config import Config, ConfigError, load_config
from topdim.db.database import Database
from topdim.handlers import get_routers
from topdim.locales import uz

logger = logging.getLogger("topdim")


def create_dispatcher(db: Database, config: Config) -> Dispatcher:
    """Dispatcher yaratadi va routerlarni ulaydi.

    ``dp["db"]`` kabi qo'shilgan obyektlar handlerlarga avtomatik uzatiladi:
    handler parametrida ``db: Database`` deb yozish kifoya.
    """
    # MemoryStorage: FSM holatlari xotirada. Bot qayta ishga tushsa, yarim
    # qolgan e'lonlar unutiladi — kichik loyiha uchun bu yetarli.
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["config"] = config
    dp.include_routers(*get_routers())
    return dp


async def set_commands(bot: Bot) -> None:
    """Telegram'dagi «Menu» tugmasida ko'rinadigan buyruqlar."""
    await bot.set_my_commands(
        [BotCommand(command=name, description=text) for name, text in uz.COMMANDS.items()]
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    try:
        config = load_config()
    except ConfigError as error:
        logger.error("%s", error)
        sys.exit(1)

    db = Database(config.db_path)
    await db.connect()
    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher(db, config)

    try:
        await set_commands(bot)
        me = await bot.get_me()
        logger.info("Bot ishga tushdi: @%s", me.username)
        await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        logger.error("BOT_TOKEN noto'g'ri. .env fayldagi tokenni @BotFather'dan qayta tekshiring.")
        sys.exit(1)
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")
