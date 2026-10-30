from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass
class ChatConfig:
    movies_topic_id: int | None = None
    groceries_topic_id: int | None = None


class BotConfig:
    """Registered groups, their topics and the bot owner. Stored in the DB, cached in memory.

    The owner is the only user who may register groups with /setup. It is `owner_id` from the
    environment if set, otherwise whoever runs /setup first.
    """

    MOVIES_TOPIC = "movies_topic_id"
    GROCERIES_TOPIC = "groceries_topic_id"

    def __init__(self, pool: asyncpg.Pool, owner_id: int | None = None) -> None:
        self._pool = pool
        self._env_owner = owner_id
        self._stored_owner: int | None = None
        self._chats: dict[int, ChatConfig] = {}

    async def load(self) -> None:
        owner = await self._pool.fetchval("SELECT value FROM config WHERE key = 'owner_id'")
        self._stored_owner = int(owner) if owner else None
        rows = await self._pool.fetch("SELECT chat_id, movies_topic_id, groceries_topic_id FROM chats")
        self._chats = {
            r["chat_id"]: ChatConfig(r["movies_topic_id"], r["groceries_topic_id"]) for r in rows
        }

    # --- owner ---
    @property
    def owner_id(self) -> int | None:
        return self._env_owner or self._stored_owner

    async def claim_owner(self, user_id: int) -> None:
        """Make `user_id` the owner if there is none yet."""
        if self.owner_id is not None:
            return
        await self._pool.execute(
            "INSERT INTO config (key, value) VALUES ('owner_id', $1) ON CONFLICT (key) DO NOTHING",
            str(user_id),
        )
        self._stored_owner = int(await self._pool.fetchval("SELECT value FROM config WHERE key = 'owner_id'"))

    # --- chats ---
    def is_registered(self, chat_id: int) -> bool:
        return chat_id in self._chats

    async def register(self, chat_id: int) -> None:
        await self._pool.execute("INSERT INTO chats (chat_id) VALUES ($1) ON CONFLICT DO NOTHING", chat_id)
        self._chats.setdefault(chat_id, ChatConfig())

    def movies_topic(self, chat_id: int) -> int | None:
        return self._chats.get(chat_id, ChatConfig()).movies_topic_id

    def groceries_topic(self, chat_id: int) -> int | None:
        return self._chats.get(chat_id, ChatConfig()).groceries_topic_id

    async def set_topic(self, chat_id: int, field: str, topic_id: int | None) -> None:
        assert field in (self.MOVIES_TOPIC, self.GROCERIES_TOPIC)
        await self._pool.execute(f"UPDATE chats SET {field} = $2 WHERE chat_id = $1", chat_id, topic_id)
        setattr(self._chats[chat_id], field, topic_id)

    async def clear_topic(self, chat_id: int, topic_id: int) -> None:
        chat = self._chats[chat_id]
        for field in (self.MOVIES_TOPIC, self.GROCERIES_TOPIC):
            if getattr(chat, field) == topic_id:
                await self.set_topic(chat_id, field, None)
