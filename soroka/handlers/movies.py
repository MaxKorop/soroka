from __future__ import annotations

import html
from collections import defaultdict

import asyncpg
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from .. import texts

router = Router(name="movies")

DEFAULT_GENRE = "Без жанру"


def _who(message: Message) -> str | None:
    return message.from_user.first_name if message.from_user else None


@router.message(Command("movie_add"))
async def movie_add(message: Message, command: CommandObject, pool: asyncpg.Pool) -> None:
    if not command.args:
        await message.reply(texts.MOVIE_USAGE)
        return
    title, _, genre = command.args.partition("|")
    title, genre = title.strip(), genre.strip() or DEFAULT_GENRE
    if not title:
        await message.reply(texts.MOVIE_USAGE)
        return
    await pool.execute(
        "INSERT INTO movies (title, genre, added_by) VALUES ($1, $2, $3)", title, genre, _who(message)
    )
    await message.reply(texts.MOVIE_ADDED.format(title=html.escape(title), genre=html.escape(genre)))


@router.message(Command("movies"))
async def movies(message: Message, pool: asyncpg.Pool) -> None:
    rows = await pool.fetch("SELECT id, title, genre, watched FROM movies ORDER BY genre, title")
    if not rows:
        await message.reply(texts.MOVIES_EMPTY)
        return

    sections = {False: texts.MOVIES_HEADER, True: texts.WATCHED_HEADER}
    parts: list[str] = []
    for watched, header in sections.items():
        by_genre: dict[str, list[str]] = defaultdict(list)
        for r in (r for r in rows if r["watched"] == watched):
            by_genre[r["genre"]].append(f"  {r['id']}. {html.escape(r['title'])}")
        if not by_genre:
            continue
        parts.append(f"<b>{header}</b>")
        for genre, lines in by_genre.items():
            parts.append(f"\n<i>{html.escape(genre)}</i>")
            parts.extend(lines)
        parts.append("")
    await message.reply("\n".join(parts).strip())


@router.message(Command("movie_done"))
async def movie_done(message: Message, command: CommandObject, pool: asyncpg.Pool) -> None:
    if not command.args or not command.args.strip().isdigit():
        await message.reply(texts.MOVIE_DONE_USAGE)
        return
    title = await pool.fetchval(
        "UPDATE movies SET watched = TRUE, watched_at = now() WHERE id = $1 AND NOT watched RETURNING title",
        int(command.args),
    )
    if title is None:
        await message.reply(texts.MOVIE_NOT_FOUND)
        return
    await message.reply(texts.MOVIE_DONE.format(title=html.escape(title)))
