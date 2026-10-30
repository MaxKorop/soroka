"""Stopgap groceries + meal planning; to be replaced by the separate app."""
from __future__ import annotations

import html

import asyncpg
from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from .. import texts
from ..botconfig import BotConfig
from .common import say

router = Router(name="groceries")


def _id_arg(command: CommandObject) -> int | None:
    arg = (command.args or "").strip()
    return int(arg) if arg.isdigit() else None


@router.message(Command("need"))
async def need(message: Message, bot: Bot, config: BotConfig, command: CommandObject, pool: asyncpg.Pool) -> None:
    item = (command.args or "").strip()
    if not item:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.NEED_USAGE)
        return
    who = message.from_user.first_name if message.from_user else None
    await pool.execute("INSERT INTO groceries (item, added_by, chat_id) VALUES ($1, $2, $3)", item, who, message.chat.id
    )
    await say(message, bot, config.groceries_topic(message.chat.id), texts.NEED_ADDED.format(item=html.escape(item)))


@router.message(Command("needed"))
async def needed(message: Message, bot: Bot, config: BotConfig, pool: asyncpg.Pool) -> None:
    rows = await pool.fetch("SELECT id, item FROM groceries WHERE chat_id = $1 AND NOT bought ORDER BY id", message.chat.id
    )
    if not rows:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.NEED_EMPTY)
        return
    lines = [f"<b>{texts.NEED_HEADER}</b>"] + [f"{r['id']}. {html.escape(r['item'])}" for r in rows]
    await say(message, bot, config.groceries_topic(message.chat.id), "\n".join(lines))


@router.message(Command("got"))
async def got(message: Message, bot: Bot, config: BotConfig, command: CommandObject, pool: asyncpg.Pool) -> None:
    item_id = _id_arg(command)
    if item_id is None:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.GOT_USAGE)
        return
    item = await pool.fetchval(
        "UPDATE groceries SET bought = TRUE WHERE id = $1 AND chat_id = $2 AND NOT bought RETURNING item",
        item_id,
        message.chat.id,
    )
    if item is None:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.GOT_NOT_FOUND)
        return
    await say(message, bot, config.groceries_topic(message.chat.id), texts.GOT_DONE.format(item=html.escape(item)))


@router.message(Command("cook"))
async def cook(message: Message, bot: Bot, config: BotConfig, command: CommandObject, pool: asyncpg.Pool) -> None:
    if not command.args:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.COOK_USAGE)
        return
    dish, _, planned = command.args.partition("|")
    dish = dish.strip()
    if not dish:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.COOK_USAGE)
        return
    await pool.execute("INSERT INTO meals (dish, planned, chat_id) VALUES ($1, $2, $3)", dish, planned.strip() or None, message.chat.id
    )
    await say(message, bot, config.groceries_topic(message.chat.id), texts.COOK_ADDED.format(dish=html.escape(dish)))


@router.message(Command("menu"))
async def menu(message: Message, bot: Bot, config: BotConfig, pool: asyncpg.Pool) -> None:
    rows = await pool.fetch("SELECT id, dish, planned FROM meals WHERE chat_id = $1 AND NOT cooked ORDER BY id", message.chat.id
    )
    if not rows:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.COOK_EMPTY)
        return
    lines = [f"<b>{texts.COOK_HEADER}</b>"]
    for r in rows:
        when = f" — {html.escape(r['planned'])}" if r["planned"] else ""
        lines.append(f"{r['id']}. {html.escape(r['dish'])}{when}")
    await say(message, bot, config.groceries_topic(message.chat.id), "\n".join(lines))


@router.message(Command("cooked"))
async def cooked(message: Message, bot: Bot, config: BotConfig, command: CommandObject, pool: asyncpg.Pool) -> None:
    meal_id = _id_arg(command)
    if meal_id is None:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.COOK_DONE_USAGE)
        return
    dish = await pool.fetchval(
        "UPDATE meals SET cooked = TRUE WHERE id = $1 AND chat_id = $2 AND NOT cooked RETURNING dish",
        meal_id,
        message.chat.id,
    )
    if dish is None:
        await say(message, bot, config.groceries_topic(message.chat.id), texts.GOT_NOT_FOUND)
        return
    await say(message, bot, config.groceries_topic(message.chat.id), texts.COOK_DONE.format(dish=html.escape(dish)))


@router.message(Command("need_del"))
async def need_del(message: Message, bot: Bot, config: BotConfig, command: CommandObject, pool: asyncpg.Pool) -> None:
    topic = config.groceries_topic(message.chat.id)
    item_id = _id_arg(command)
    if item_id is None:
        await say(message, bot, topic, texts.NEED_DEL_USAGE)
        return
    item = await pool.fetchval(
        "DELETE FROM groceries WHERE id = $1 AND chat_id = $2 RETURNING item", item_id, message.chat.id
    )
    if item is None:
        await say(message, bot, topic, texts.GOT_NOT_FOUND)
        return
    await say(message, bot, topic, texts.NEED_DELETED.format(item=html.escape(item)))


@router.message(Command("cook_del"))
async def cook_del(message: Message, bot: Bot, config: BotConfig, command: CommandObject, pool: asyncpg.Pool) -> None:
    topic = config.groceries_topic(message.chat.id)
    meal_id = _id_arg(command)
    if meal_id is None:
        await say(message, bot, topic, texts.COOK_DEL_USAGE)
        return
    dish = await pool.fetchval(
        "DELETE FROM meals WHERE id = $1 AND chat_id = $2 RETURNING dish", meal_id, message.chat.id
    )
    if dish is None:
        await say(message, bot, topic, texts.GOT_NOT_FOUND)
        return
    await say(message, bot, topic, texts.COOK_DELETED.format(dish=html.escape(dish)))
