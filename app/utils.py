import re
from urllib.parse import parse_qs, urlparse

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtube-nocookie.com"}
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")

def normalize_youtube_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().split(":")[0]
    if host not in YOUTUBE_HOSTS:
        raise ValueError("Only YouTube URLs are supported")
    video_id = None
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    elif parsed.path.startswith(("/shorts/", "/embed/", "/live/")):
        video_id = parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else None
    if not video_id or not VIDEO_ID_RE.match(video_id):
        raise ValueError("Invalid or unsupported YouTube video URL")
    return f"https://www.youtube.com/watch?v={video_id}"

def format_number(value: int | None) -> str:
    if value is None: return "N/A"
    if value >= 1_000_000_000: return f"{value / 1_000_000_000:.1f}B".replace(".0B", "B")
    if value >= 1_000_000: return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000: return f"{value / 1_000:.1f}K".replace(".0K", "K")
    return f"{value:,}"

def format_duration(seconds: int | None) -> str:
    if seconds is None: return "N/A"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600); m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")

def format_size(size: int | None) -> str:
    if not size: return "Unknown"
    units = ["B", "KB", "MB", "GB"]
    n = float(size)
    for unit in units:
        if n < 1024 or unit == "GB": return f"{n:.1f} {unit}"
        n /= 1024
    return "Unknown"
