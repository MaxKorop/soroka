from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.types import FSInputFile, Message

from .. import texts
from ..config import Settings
from ..services import downloader

log = logging.getLogger(__name__)
router = Router(name="videos")

# 1 GB VM: don't run more than two downloads/encodes at once.
_slots = asyncio.Semaphore(2)


@router.message(F.text | F.caption)
async def grab_videos(message: Message, bot: Bot, settings: Settings) -> None:
    urls = downloader.find_video_urls(message.text or message.caption or "")
    if not urls:
        return

    sender = message.from_user.full_name if message.from_user else "хтось"
    posted_any = False

    for url in urls:
        async with _slots:
            try:
                video, tmp = await downloader.download(url, settings.cookies_path, settings.max_video_bytes)
            except downloader.TooLargeError:
                await message.reply(texts.VIDEO_TOO_BIG.format(url=url))
                continue
            except downloader.DownloadError:
                log.exception("download failed: %s", url)
                await message.reply(texts.VIDEO_FAILED)
                continue

            try:
                await bot.send_video(
                    chat_id=settings.group_id,
                    message_thread_id=settings.videos_topic_id,
                    video=FSInputFile(video.path),
                    caption=f"{texts.VIDEO_CAPTION}\n{texts.VIDEO_FROM.format(name=sender)}",
                    width=video.width,
                    height=video.height,
                    duration=video.duration,
                    supports_streaming=True,
                )
                posted_any = True
            except Exception:
                log.exception("upload failed: %s", url)
                await message.reply(texts.VIDEO_FAILED)
            finally:
                tmp.cleanup()

    if posted_any and settings.delete_original:
        try:
            await message.delete()
        except Exception:
            log.warning("could not delete original message (needs admin 'delete messages')")
