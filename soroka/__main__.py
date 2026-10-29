from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from . import texts
from .config import load_settings
from .db import create_pool
from .handlers import groceries, movies, videos


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    pool = await create_pool(settings.database_url)

    # Video uploads can take a while on a small VM.
    bot = Bot(
        settings.bot_token,
        session=AiohttpSession(timeout=300),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(settings=settings, pool=pool)

    # Commands first, so the link grabber (catch-all on text) never swallows them.
    routers = (movies.router, groceries.router, videos.router)
    dp.include_routers(*routers)

    # Only ever react inside our private group (filters don't propagate to child routers).
    in_group = F.chat.id == settings.group_id
    for r in (dp, *routers):
        r.message.filter(in_group)

    @dp.message(Command("start", "help"))
    async def help_(message: Message) -> None:
        await message.reply(texts.HELP)

    try:
        await dp.start_polling(bot)
    finally:
        await pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
