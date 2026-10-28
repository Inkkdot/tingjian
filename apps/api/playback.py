"""Playback URL adapters and capability labels."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse


def clamp_start(start_ms: int, offset_ms: int = 0) -> int:
    return max(0, int(start_ms) + int(offset_ms))


def bilibili_url(platform_video_id: str, part_index: int, start_ms: int, offset_ms: int = 0) -> str:
    t = clamp_start(start_ms, offset_ms) // 1000
    p = max(1, int(part_index or 1))
    return f"https://www.bilibili.com/video/{platform_video_id}?p={p}&t={t}"


def youtube_url(platform_video_id: str, start_ms: int, offset_ms: int = 0) -> str:
    t = clamp_start(start_ms, offset_ms) // 1000
    return f"https://www.youtube.com/watch?v={platform_video_id}&t={t}s"


def jump_for(
    *,
    platform: str,
    source_url: str,
    platform_video_id: str,
    part_index: int,
    start_ms: int,
    offset_ms: int = 0,
) -> tuple[str, str]:
    """Return (jump_url, playback_capability)."""
    if platform == "bilibili" and platform_video_id:
        return bilibili_url(platform_video_id, part_index, start_ms, offset_ms), "external_seek"
    if platform == "youtube" and platform_video_id:
        return youtube_url(platform_video_id, start_ms, offset_ms), "external_seek"
    if source_url.startswith(("http://", "https://")):
        host = urlparse(source_url).netloc.lower()
        if "bilibili.com" in host:
            bvid = _bvid_from_url(source_url)
            if bvid:
                return bilibili_url(bvid, part_index, start_ms, offset_ms), "external_seek"
        if "youtube.com" in host or "youtu.be" in host:
            vid = _youtube_id(source_url)
            if vid:
                return youtube_url(vid, start_ms, offset_ms), "external_seek"
        sep = "&" if "?" in source_url else "?"
        return f"{source_url}{sep}t={clamp_start(start_ms, offset_ms) / 1000:.1f}", "url_hint"
    return "", "local_select"


def _bvid_from_url(url: str) -> str | None:
    for part in urlparse(url).path.split("/"):
        if part.startswith("BV") and len(part) >= 10:
            return part
    return None


def _youtube_id(url: str) -> str | None:
    parsed = urlparse(url)
    if "youtu.be" in parsed.netloc:
        return parsed.path.strip("/") or None
    return (parse_qs(parsed.query).get("v") or [None])[0]
