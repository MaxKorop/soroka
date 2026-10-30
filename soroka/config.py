from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    bot_token: str
    database_url: str

    # Optional: Telegram user id of the owner. If empty, the first person to run /setup becomes the owner.
    owner_id: int = 0
    # Optional: fills in the genre when /movie_add is called without one.
    tmdb_api_key: str = ""

    cookies_file: str = ""
    max_video_bytes: int = 50 * 1024 * 1024

    @property
    def cookies_path(self) -> Path | None:
        if self.cookies_file and Path(self.cookies_file).is_file():
            return Path(self.cookies_file)
        return None


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
