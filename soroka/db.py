from __future__ import annotations

from pathlib import Path

import asyncpg

SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


async def create_pool(dsn: str) -> asyncpg.Pool:
    # Neon suspends idle compute and may sit behind pgbouncer: drop idle
    # connections quickly and avoid server-side prepared statements.
    pool = await asyncpg.create_pool(
        dsn,
        min_size=0,
        max_size=3,
        max_inactive_connection_lifetime=60,
        statement_cache_size=0,
        timeout=30,
        command_timeout=30,
    )
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)
    return pool
