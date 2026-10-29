from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    group_id: int
    videos_topic_id: int
    database_url: str

    cookies_file: str = ""
    delete_original: bool = False
    max_video_bytes: int = 50 * 1024 * 1024

    @property
    def cookies_path(self) -> Path | None:
        if self.cookies_file and Path(self.cookies_file).is_file():
            return Path(self.cookies_file)
        return None


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
