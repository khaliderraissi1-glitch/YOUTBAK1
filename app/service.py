import os
import secrets
import time
from typing import Any
import yt_dlp
from .config import get_settings
from .utils import format_duration, format_number, format_size, normalize_youtube_url

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}

def _base_url(request_base: str) -> str:
    settings = get_settings()
    return settings.public_base_url.rstrip("/") or request_base.rstrip("/")

def _ydl_opts() -> dict[str, Any]:
    settings = get_settings()
    opts: dict[str, Any] = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "skip_download": True, "extractor_args": {"youtube": {"player_client": ["web", "android"]}},
    }
    if settings.cookies_file and os.path.exists(settings.cookies_file): opts["cookiefile"] = settings.cookies_file
    return opts

def _pick_format(info: dict, kind: str) -> tuple[str | None, int | None, str]:
    formats = info.get("formats") or []
    if kind == "video_hd":
        candidates = [f for f in formats if f.get("ext") == "mp4" and f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none") and f.get("url")]
        candidates.sort(key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
        label = f"{candidates[0].get('height')}p" if candidates else "Best"
    elif kind == "video_sd":
        candidates = [f for f in formats if f.get("ext") == "mp4" and f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none") and f.get("url") and (f.get("height") or 0) <= 480]
        candidates.sort(key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
        label = f"{candidates[0].get('height')}p" if candidates else "480p"
    else:
        candidates = [f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none") and f.get("url")]
        candidates.sort(key=lambda f: (f.get("abr") or 0, f.get("filesize") or 0), reverse=True)
        label = "MP3"
    if not candidates: return None, None, label
    selected = candidates[0]
    return selected.get("format_id"), selected.get("filesize") or selected.get("filesize_approx"), label

def get_cached(token: str) -> dict[str, Any] | None:
    item = _CACHE.get(token)
    if not item: return None
    if item[0] < time.time(): _CACHE.pop(token, None); return None
    return item[1]

def extract_video(url: str, request_base: str) -> dict[str, Any]:
    canonical = normalize_youtube_url(url)
    with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
        info = ydl.extract_info(canonical, download=False)
    duration = info.get("duration")
    settings = get_settings()
    if duration and duration > settings.max_video_seconds: raise ValueError(f"Video is longer than the {settings.max_video_seconds // 60}-minute limit")
    token = secrets.token_urlsafe(18)
    payload = {"canonical_url": canonical, "info": info}
    _CACHE[token] = (time.time() + settings.cache_ttl_seconds, payload)
    base = _base_url(request_base)
    downloads = []
    for kind, label, fmt in [("video_hd", "Video HD", "MP4"), ("video_sd", "Video SD", "MP4"), ("audio_mp3", "Audio", "MP3")]:
        format_id, size, quality = _pick_format(info, kind)
        if format_id:
            downloads.append({"id": kind, "label": label, "format": fmt, "quality": quality, "file_size": format_size(size), "size_bytes": size, "download_url": f"{base}/api/download/{token}/{kind}"})
    return {"video_id": info.get("id"), "url": canonical, "title": info.get("title") or "YouTube video", "thumbnail": info.get("thumbnail"), "author": info.get("uploader") or info.get("channel"), "channel_url": info.get("channel_url"), "duration_seconds": duration, "duration": format_duration(duration), "views": info.get("view_count"), "views_formatted": format_number(info.get("view_count")), "upload_date": info.get("upload_date"), "downloads": downloads}
