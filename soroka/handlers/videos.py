from __future__ import annotations

import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.types import FSInputFile, Message

from .. import texts
from ..config import Settings
from ..services import downloader

log = logging.getLogger(__name__)
router = Router(name="videos")

# 1 GB VM: don't run more than two downloads/encodes at once.
_slots = asyncio.Semaphore(2)


@router.message(F.text | F.caption)
async def grab_videos(message: Message, settings: Settings) -> None:
    urls = downloader.find_video_urls(message.text or message.caption or "")
    if not urls:
        return

    sender = message.from_user.full_name if message.from_user else "хтось"

    for url in urls:
        # Telegram can't turn a text message into a video, so: status reply -> video reply -> delete status.
        status = await message.reply(texts.VIDEO_WORKING)
        async with _slots:
            try:
                video, tmp = await downloader.download(url, settings.cookies_path, settings.max_video_bytes)
            except downloader.TooLargeError:
                await status.edit_text(texts.VIDEO_TOO_BIG.format(url=html.escape(url)))
                continue
            except downloader.DownloadError:
                log.exception("download failed: %s", url)
                await status.edit_text(texts.VIDEO_FAILED)
                continue

            try:
                # Replies to the link message, so it lands in the same topic.
                await message.reply_video(
                    video=FSInputFile(video.path),
                    caption=f"{texts.VIDEO_CAPTION}\n{texts.VIDEO_FROM.format(name=html.escape(sender))}",
                    width=video.width,
                    height=video.height,
                    duration=video.duration,
                    supports_streaming=True,
                )
                await status.delete()
            except Exception:
                log.exception("upload failed: %s", url)
                await status.edit_text(texts.VIDEO_FAILED)
            finally:
                tmp.cleanup()
