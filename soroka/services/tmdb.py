from __future__ import annotations

import logging

import aiohttp

log = logging.getLogger(__name__)

_BASE = "https://api.themoviedb.org/3"
_LANG = "uk-UA"
_genres: dict[int, str] = {}


async def _load_genres(session: aiohttp.ClientSession, api_key: str) -> None:
    async with session.get(f"{_BASE}/genre/movie/list", params={"api_key": api_key, "language": _LANG}) as r:
        r.raise_for_status()
        data = await r.json()
    _genres.update({g["id"]: g["name"] for g in data["genres"]})


async def lookup_genre(api_key: str, title: str) -> str | None:
    """Primary TMDB genre of the best match for `title`, or None if unknown or on any failure."""
    if not api_key:
        return None
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            if not _genres:
                await _load_genres(session, api_key)
            params = {"api_key": api_key, "query": title, "language": _LANG}
            async with session.get(f"{_BASE}/search/movie", params=params) as r:
                r.raise_for_status()
                results = (await r.json())["results"]
    except Exception:
        log.warning("TMDB lookup failed for %r", title, exc_info=True)
        return None

    for movie in results[:1]:
        for genre_id in movie.get("genre_ids", []):
            if genre_id in _genres:
                return _genres[genre_id].capitalize()
    return None
