from __future__ import annotations

from contextlib import suppress

from aiogram import Bot
from aiogram.types import Message, ReactionTypeEmoji


def thread_of(message: Message) -> int | None:
    return message.message_thread_id if message.is_topic_message else None


async def say(message: Message, bot: Bot, topic_id: int | None, text: str) -> None:
    """Reply in place, or post into the feature's dedicated topic (and 👌 the original) if one is set."""
    if not topic_id or topic_id == thread_of(message):
        await message.reply(text)
        return
    await bot.send_message(message.chat.id, text, message_thread_id=topic_id)
    with suppress(Exception):
        await message.react([ReactionTypeEmoji(emoji="👌")])
