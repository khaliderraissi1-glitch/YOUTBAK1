from typing import Literal
from pydantic import BaseModel, Field, HttpUrl

class VideoRequest(BaseModel):
    url: HttpUrl = Field(..., description="YouTube video URL")

class DownloadItem(BaseModel):
    id: Literal["video_hd", "video_sd", "audio_mp3"]
    label: str
    format: str
    quality: str
    file_size: str
    size_bytes: int | None = None
    download_url: str

class VideoInfo(BaseModel):
    video_id: str
    url: str
    title: str
    thumbnail: str | None = None
    author: str | None = None
    channel_url: str | None = None
    duration_seconds: int | None = None
    duration: str
    views: int | None = None
    views_formatted: str
    upload_date: str | None = None
    downloads: list[DownloadItem]

class ErrorResponse(BaseModel):
    detail: str
