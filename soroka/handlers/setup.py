"""In-chat configuration: /setup registers the group, /here assigns the current topic to a feature."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .. import texts
from ..botconfig import BotConfig
from ..config import Settings
from .common import thread_of

# /setup must work before any group is known, so this router has no group filter.
router = Router(name="setup")
# /here and its buttons only work inside the registered group.
gated_router = Router(name="here")

_FEATURES = {
    "movies": (BotConfig.MOVIES_TOPIC, texts.HERE_SAVED_MOVIES),
    "groceries": (BotConfig.GROCERIES_TOPIC, texts.HERE_SAVED_GROCERIES),
}


def in_group(message: Message, config: BotConfig) -> bool:
    return config.is_registered(message.chat.id)


@router.message(Command("setup"))
async def setup(message: Message, config: BotConfig) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await message.reply(texts.SETUP_PRIVATE)
        return
    user = message.from_user
    if user is None:  # e.g. anonymous admin: can't tell who it is
        await message.reply(texts.SETUP_NOT_OWNER)
        return
    await config.claim_owner(user.id)
    if user.id != config.owner_id:
        await message.reply(texts.SETUP_NOT_OWNER)
        return
    if config.is_registered(message.chat.id):
        await message.reply(texts.SETUP_ALREADY)
        return
    await config.register(message.chat.id)
    note = "" if message.chat.is_forum else texts.SETUP_NOT_FORUM
    await message.reply(texts.SETUP_DONE + note)


def _topic_line(label: str, chat_id: int, topic_id: int | None) -> str:
    if topic_id is None:
        return f"{label}: {texts.CONFIG_NOT_SET}"
    chat = str(chat_id)
    if chat.startswith("-100"):
        return f'{label}: <a href="https://t.me/c/{chat[4:]}/{topic_id}">тема #{topic_id}</a>'
    return f"{label}: тема #{topic_id}"


@router.message(Command("config", "status"))
async def show_config(message: Message, config: BotConfig, settings: Settings) -> None:
    chat_id = message.chat.id
    if not config.is_registered(chat_id):
        await message.reply(texts.CONFIG_UNREGISTERED)
        return
    yes, no = "✅", "—"
    lines = [
        f"<b>{texts.CONFIG_HEADER}</b>",
        f"Група: <code>{chat_id}</code>",
        f"Теми: {yes if message.chat.is_forum else no} " + ("увімкнені" if message.chat.is_forum else "вимкнені"),
        _topic_line("🎬 Фільми", chat_id, config.movies_topic(chat_id)),
        _topic_line("🛒 Продукти й меню", chat_id, config.groceries_topic(chat_id)),
        f"🎞 TMDB (автожанр): {yes if settings.tmdb_api_key else no}",
        f"🍪 Cookies для Instagram: {yes if settings.cookies_path else no}",
    ]
    user = message.from_user
    if user and user.id == config.owner_id:
        lines.append("👑 Ти — господар гнізда")
    await message.reply("\n".join(lines))


@gated_router.message(Command("here"))
async def here(message: Message) -> None:
    if thread_of(message) is None:
        await message.reply(texts.HERE_NO_TOPIC)
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.HERE_MOVIES, callback_data="here:movies")],
            [InlineKeyboardButton(text=texts.HERE_GROCERIES, callback_data="here:groceries")],
            [InlineKeyboardButton(text=texts.HERE_CLEAR, callback_data="here:clear")],
        ]
    )
    await message.reply(texts.HERE_ASK, reply_markup=keyboard)


@gated_router.callback_query(F.data.startswith("here:"))
async def here_chosen(query: CallbackQuery, config: BotConfig) -> None:
    msg = query.message
    if not isinstance(msg, Message) or not config.is_registered(msg.chat.id):
        await query.answer()
        return
    topic = thread_of(msg)
    choice = (query.data or "").split(":", 1)[1]
    if topic is None:
        await query.answer(texts.HERE_NO_TOPIC, show_alert=True)
        return

    if choice == "clear":
        await config.clear_topic(msg.chat.id, topic)
        result = texts.HERE_CLEARED
    elif choice in _FEATURES:
        key, result = _FEATURES[choice]
        await config.set_topic(msg.chat.id, key, topic)
    else:
        await query.answer()
        return

    await msg.edit_text(result)
    await query.answer()
