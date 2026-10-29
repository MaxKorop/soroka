"""Stopgap groceries + meal planning; to be replaced by the separate app."""
from __future__ import annotations

import html

import asyncpg
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from .. import texts

router = Router(name="groceries")


def _id_arg(command: CommandObject) -> int | None:
    arg = (command.args or "").strip()
    return int(arg) if arg.isdigit() else None


@router.message(Command("need"))
async def need(message: Message, command: CommandObject, pool: asyncpg.Pool) -> None:
    item = (command.args or "").strip()
    if not item:
        await message.reply(texts.NEED_USAGE)
        return
    who = message.from_user.first_name if message.from_user else None
    await pool.execute("INSERT INTO groceries (item, added_by) VALUES ($1, $2)", item, who)
    await message.reply(texts.NEED_ADDED.format(item=html.escape(item)))


@router.message(Command("needed"))
async def needed(message: Message, pool: asyncpg.Pool) -> None:
    rows = await pool.fetch("SELECT id, item FROM groceries WHERE NOT bought ORDER BY id")
    if not rows:
        await message.reply(texts.NEED_EMPTY)
        return
    lines = [f"<b>{texts.NEED_HEADER}</b>"] + [f"{r['id']}. {html.escape(r['item'])}" for r in rows]
    await message.reply("\n".join(lines))


@router.message(Command("got"))
async def got(message: Message, command: CommandObject, pool: asyncpg.Pool) -> None:
    item_id = _id_arg(command)
    if item_id is None:
        await message.reply(texts.GOT_USAGE)
        return
    item = await pool.fetchval(
        "UPDATE groceries SET bought = TRUE WHERE id = $1 AND NOT bought RETURNING item", item_id
    )
    if item is None:
        await message.reply(texts.GOT_NOT_FOUND)
        return
    await message.reply(texts.GOT_DONE.format(item=html.escape(item)))


@router.message(Command("cook"))
async def cook(message: Message, command: CommandObject, pool: asyncpg.Pool) -> None:
    if not command.args:
        await message.reply(texts.COOK_USAGE)
        return
    dish, _, planned = command.args.partition("|")
    dish = dish.strip()
    if not dish:
        await message.reply(texts.COOK_USAGE)
        return
    await pool.execute("INSERT INTO meals (dish, planned) VALUES ($1, $2)", dish, planned.strip() or None)
    await message.reply(texts.COOK_ADDED.format(dish=html.escape(dish)))


@router.message(Command("menu"))
async def menu(message: Message, pool: asyncpg.Pool) -> None:
    rows = await pool.fetch("SELECT id, dish, planned FROM meals WHERE NOT cooked ORDER BY id")
    if not rows:
        await message.reply(texts.COOK_EMPTY)
        return
    lines = [f"<b>{texts.COOK_HEADER}</b>"]
    for r in rows:
        when = f" — {html.escape(r['planned'])}" if r["planned"] else ""
        lines.append(f"{r['id']}. {html.escape(r['dish'])}{when}")
    await message.reply("\n".join(lines))


@router.message(Command("cooked"))
async def cooked(message: Message, command: CommandObject, pool: asyncpg.Pool) -> None:
    meal_id = _id_arg(command)
    if meal_id is None:
        await message.reply(texts.COOK_DONE_USAGE)
        return
    dish = await pool.fetchval(
        "UPDATE meals SET cooked = TRUE WHERE id = $1 AND NOT cooked RETURNING dish", meal_id
    )
    if dish is None:
        await message.reply(texts.GOT_NOT_FOUND)
        return
    await message.reply(texts.COOK_DONE.format(dish=html.escape(dish)))
