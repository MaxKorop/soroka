from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from . import texts
from .botconfig import BotConfig
from .config import load_settings
from .db import create_pool
from .handlers import groceries, movies, setup, videos


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
    config = BotConfig(pool, settings.owner_id or None)
    await config.load()
    dp = Dispatcher(settings=settings, pool=pool, config=config)

    core = Router(name="core")

    @core.message(Command("start", "help"))
    async def help_(message: Message) -> None:
        await message.reply(texts.HELP)

    # /help and /setup work anywhere (/setup is owner only and registers the group); everything
    # else only inside registered groups. Filters go on each leaf router, never on `dp`: a failing root filter
    # stops propagation into child routers. Commands come before the link grabber's catch-all.
    gated = (setup.gated_router, movies.router, groceries.router, videos.router)
    dp.include_routers(core, setup.router, *gated)
    for r in gated:
        r.message.filter(setup.in_group)

    try:
        await dp.start_polling(bot)
    finally:
        await pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
