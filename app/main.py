import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yt_dlp
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask
from slowapi import Limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .models import VideoRequest
from .service import extract_video, get_cached, _pick_format, _ydl_opts
from .utils import normalize_youtube_url

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="YouTube metadata and media download API",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"name": settings.app_name, "status": "ok", "docs": "/docs", "endpoint": "GET /info?url=..."}


@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "youtube-backend"}


def _info_response(url: str, request: Request):
    try:
        return extract_video(url, str(request.base_url))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to process YouTube URL: {exc}") from exc


@app.post("/api/info")
@limiter.limit(settings.rate_limit)
def info(body: VideoRequest, request: Request):
    return _info_response(str(body.url), request)


@app.get("/info")
@app.get("/api/info")
@limiter.limit(settings.rate_limit)
def info_get(url: str, request: Request):
    return _info_response(url, request)


def _audio_file(canonical_url: str, format_id: str) -> FileResponse:
    tempdir = tempfile.mkdtemp(prefix="youtube-")
    out = os.path.join(tempdir, "audio.%(ext)s")
    opts = _ydl_opts() | {
        "format": format_id,
        "outtmpl": out,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([canonical_url])
        mp3 = next(Path(tempdir).glob("audio.mp3"), None)
        if not mp3:
            raise RuntimeError("MP3 conversion failed; ensure ffmpeg is installed")
        return FileResponse(
            mp3,
            media_type="audio/mpeg",
            filename="youtube-audio.mp3",
            background=BackgroundTask(shutil.rmtree, tempdir, ignore_errors=True),
        )
    except Exception:
        shutil.rmtree(tempdir, ignore_errors=True)
        raise


def _video_stream(info: dict[str, Any], format_id: str):
    selected = next(
        (item for item in info.get("formats", []) if item.get("format_id") == format_id),
        None,
    )
    if not selected or not selected.get("url"):
        raise RuntimeError("Media URL unavailable")
    ext = (selected.get("ext") or "mp4").lower()
    media_type = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
    }.get(ext, "application/octet-stream")
    filename = f"youtube-video.{ext}"
    return StreamingResponse(
        _proxy(selected["url"]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _download_from_info(canonical_url: str, info: dict[str, Any], kind: str):
    format_id, _, _ = _pick_format(info, kind)
    if not format_id:
        raise HTTPException(404, "Requested format is not available for this video")
    try:
        if kind == "audio_mp3":
            return _audio_file(canonical_url, format_id)
        return _video_stream(info, format_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Unable to fetch media: {exc}") from exc


def _extract_for_download(url: str) -> tuple[str, dict[str, Any]]:
    try:
        canonical_url = normalize_youtube_url(url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    try:
        with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
            info = ydl.extract_info(canonical_url, download=False)
        duration = info.get("duration")
        if duration and duration > settings.max_video_seconds:
            raise HTTPException(
                422,
                f"Video is longer than the {settings.max_video_seconds // 60}-minute limit",
            )
        return canonical_url, info
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to extract YouTube media: {exc}") from exc


@app.get("/download/mp4")
@limiter.limit("10/minute")
def download_mp4(url: str, request: Request):
    canonical_url, info = _extract_for_download(url)
    return _download_from_info(canonical_url, info, "video_hd")


@app.get("/download/mp3")
@limiter.limit("10/minute")
def download_mp3(url: str, request: Request):
    canonical_url, info = _extract_for_download(url)
    return _download_from_info(canonical_url, info, "audio_mp3")


@app.get("/api/download/{token}/{kind}")
@limiter.limit("10/minute")
def download(token: str, kind: str, request: Request):
    if kind not in {"video_hd", "video_sd", "audio_mp3"}:
        raise HTTPException(400, "Unsupported download type")
    cached = get_cached(token)
    if not cached:
        raise HTTPException(410, "This download link expired. Request the video information again.")
    canonical_url, info = _extract_for_download(cached["canonical_url"])
    return _download_from_info(canonical_url, info, kind)


async def _proxy(url: str):
    import httpx

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=settings.request_timeout_seconds,
    ) as client:
        async with client.stream("GET", url, headers={"User-Agent": "Mozilla/5.0"}) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(1024 * 1024):
                yield chunk
