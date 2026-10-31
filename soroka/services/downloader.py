from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

_TIKTOK_HOSTS = {"tiktok.com", "vm.tiktok.com", "vt.tiktok.com"}
_INSTAGRAM_HOSTS = {"instagram.com"}
_YOUTUBE_HOSTS = {"youtube.com", "m.youtube.com", "music.youtube.com"}

# Tried in order until the result fits into the upload limit.
# Sorted rather than filtered: `height` of a vertical video is its long side, so a `height<=720`
# filter rejects every TikTok/Reels/Shorts format and silently falls back to the best one (1080p
# HEVC), which plays back choppy in many Telegram clients. `res` is the short side.
_FORMAT = "bv*+ba/b"
_SORT_TIERS = (
    ["vcodec:h264", "res:720", "acodec:aac"],
    ["vcodec:h264", "res:360", "acodec:aac"],
)


class DownloadError(Exception):
    pass


class TooLargeError(DownloadError):
    pass


@dataclass
class Video:
    path: Path
    width: int | None
    height: int | None
    duration: int | None


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def is_supported(url: str) -> bool:
    host = _host(url)
    path = urlparse(url).path
    if host in _TIKTOK_HOSTS:
        return True
    if host in _INSTAGRAM_HOSTS:
        return path.startswith(("/reel/", "/reels/", "/p/", "/tv/"))
    if host == "youtu.be":
        return len(path) > 1
    if host in _YOUTUBE_HOSTS:
        return path.startswith(("/watch", "/shorts/"))
    return False


def find_video_urls(text: str) -> list[str]:
    urls = (u.rstrip(".,)!?") for u in URL_RE.findall(text))
    return list(dict.fromkeys(u for u in urls if is_supported(u)))


def _probe(path: Path) -> tuple[str, str]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=codec_name,pix_fmt", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    codec, _, pix_fmt = out.partition(",")
    return codec, pix_fmt


def _ensure_h264(path: Path) -> Path:
    """Re-encode to constant-frame-rate H.264/yuv420p when the source is something else (e.g. HEVC)."""
    try:
        if _probe(path) == ("h264", "yuv420p"):
            return path
    except (subprocess.SubprocessError, OSError):
        return path
    out = path.with_name("video_h264.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(path),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
         "-fps_mode", "cfr", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)],
        check=True, timeout=300,
    )
    path.unlink()
    return out


def _download_sync(url: str, out_dir: Path, cookies: Path | None, max_bytes: int) -> Video:
    last_error: Exception | None = None
    for sort in _SORT_TIERS:
        for old in out_dir.glob("*"):
            old.unlink()
        opts = {
            "format": _FORMAT,
            "format_sort": sort,
            "outtmpl": str(out_dir / "video.%(ext)s"),
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "noprogress": True,
            "no_warnings": True,
            "max_filesize": max_bytes,
            "socket_timeout": 30,
            "retries": 3,
        }
        if cookies:
            # yt-dlp writes the cookie jar back on close; keep the read-only mount untouched.
            jar = out_dir / "cookies.txt"
            shutil.copyfile(cookies, jar)
            opts["cookiefile"] = str(jar)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            last_error = e
            continue

        files = [p for p in out_dir.glob("video.*") if p.suffix != ".part"]
        if not files:
            last_error = DownloadError("yt-dlp produced no file (likely over max_filesize)")
            continue
        try:
            path = _ensure_h264(files[0])
        except (subprocess.SubprocessError, OSError) as e:
            last_error = e
            continue
        if path.stat().st_size > max_bytes:
            last_error = TooLargeError(url)
            continue
        return Video(
            path=path,
            width=info.get("width"),
            height=info.get("height"),
            duration=int(info["duration"]) if info.get("duration") else None,
        )

    if isinstance(last_error, TooLargeError):
        raise last_error
    raise DownloadError(str(last_error))


async def download(url: str, cookies: Path | None, max_bytes: int) -> tuple[Video, tempfile.TemporaryDirectory]:
    """Download `url`; the caller must `.cleanup()` the returned temp dir."""
    tmp = tempfile.TemporaryDirectory(prefix="soroka_")
    try:
        video = await asyncio.to_thread(_download_sync, url, Path(tmp.name), cookies, max_bytes)
    except BaseException:
        tmp.cleanup()
        raise
    return video, tmp
