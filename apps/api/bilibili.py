"""Bilibili URL parsing, metadata and public subtitle-track probing.

Only public, unauthenticated endpoints are used. Cookies belonging to a user
are never read or stored; logged-in export is handled by the browser script
fallback (upload SRT).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from domain import ImportFailed, RawCue

API = "https://api.bilibili.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
}
BV_RE = re.compile(r"(BV[0-9A-Za-z]{10})")


@dataclass
class BiliPart:
    cid: int
    page: int
    title: str
    duration_ms: int


@dataclass
class BiliVideo:
    bvid: str
    aid: int
    title: str
    duration_ms: int
    parts: list[BiliPart] = field(default_factory=list)
    owner: str = ""


@dataclass
class SubtitleTrack:
    lan: str
    lan_doc: str
    url: str
    is_ai: bool = False


def parse_bilibili_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url.strip())
    match = BV_RE.search(url)
    if not match:
        raise ImportFailed("BAD_URL", "无法从链接中识别 BV 号", 422, {"url": url})
    bvid = match.group(1)
    query = parse_qs(parsed.query)
    try:
        part = int((query.get("p") or ["1"])[0])
    except ValueError:
        part = 1
    t = 0
    if query.get("t"):
        try:
            t = int(query["t"][0])
        except ValueError:
            t = 0
    return {"bvid": bvid, "part_index": max(1, part), "start_seconds": max(0, t)}


class BilibiliClient:
    def __init__(self, timeout: float = 12.0):
        self._client = httpx.Client(headers=HEADERS, timeout=timeout, follow_redirects=True)
        self._guest_cookie = ""

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "BilibiliClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _ensure_guest_cookie(self) -> None:
        if self._guest_cookie:
            return
        try:
            resp = self._client.get(f"{API}/x/frontend/finger/spi")
            data = resp.json().get("data") or {}
            b3, b4 = data.get("b_3"), data.get("b_4")
            if b3:
                self._guest_cookie = f"buvid3={b3}; buvid4={b4 or ''}"
        except Exception:
            self._guest_cookie = ""

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_guest_cookie()
        headers = {"Cookie": self._guest_cookie} if self._guest_cookie else {}
        try:
            resp = self._client.get(f"{API}{path}", params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise ImportFailed("NETWORK_ERROR", "请求 B 站超时，请稍后重试", 504) from exc
        except httpx.HTTPError as exc:
            raise ImportFailed("NETWORK_ERROR", f"网络错误：{exc}", 502) from exc
        if resp.status_code == 412:
            raise ImportFailed("RATE_LIMITED", "B 站风控拦截（412），请稍后再试或用 SRT 上传", 429)
        if resp.status_code != 200:
            raise ImportFailed("NETWORK_ERROR", f"B 站返回 HTTP {resp.status_code}", 502)
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ImportFailed("NETWORK_ERROR", "B 站返回非 JSON 内容", 502) from exc
        code = payload.get("code")
        if code == -412:
            raise ImportFailed("RATE_LIMITED", "B 站风控拦截，请稍后再试或用 SRT 上传", 429)
        if code == -403:
            raise ImportFailed("ACCESS_RESTRICTED", "该视频访问受限（可能需要登录或地区限制）", 403)
        if code != 0:
            raise ImportFailed(
                "BILIBILI_API_ERROR",
                f"B 站接口错误：{payload.get('message') or code}",
                502,
                {"bili_code": code},
            )
        return payload

    def fetch_video(self, bvid: str) -> BiliVideo:
        payload = self._get_json("/x/web-interface/view", {"bvid": bvid})
        data = payload["data"]
        parts = [
            BiliPart(
                cid=int(p.get("cid") or 0),
                page=int(p.get("page") or i + 1),
                title=str(p.get("part") or data.get("title") or ""),
                duration_ms=int(p.get("duration") or 0) * 1000,
            )
            for i, p in enumerate(data.get("pages") or [])
        ]
        if not parts:
            parts = [
                BiliPart(
                    cid=int(data.get("cid") or 0),
                    page=1,
                    title=str(data.get("title") or ""),
                    duration_ms=int(data.get("duration") or 0) * 1000,
                )
            ]
        return BiliVideo(
            bvid=str(data.get("bvid") or bvid),
            aid=int(data.get("aid") or 0),
            title=str(data.get("title") or ""),
            duration_ms=int(data.get("duration") or 0) * 1000,
            parts=parts,
            owner=str((data.get("owner") or {}).get("name") or ""),
        )

    def fetch_subtitles(self, bvid: str, cid: int) -> list[SubtitleTrack]:
        payload = self._get_json("/x/player/v2", {"bvid": bvid, "cid": cid})
        subtitle = (payload.get("data") or {}).get("subtitle") or {}
        tracks = [
            SubtitleTrack(
                lan=str(t.get("lan") or ""),
                lan_doc=str(t.get("lan_doc") or ""),
                url=str(t.get("subtitle_url") or ""),
                is_ai=bool(t.get("ai_status") or t.get("is_ai_subtitle")),
            )
            for t in subtitle.get("subtitles") or []
            if t.get("subtitle_url")
        ]
        return tracks

    def fetch_cues(self, track: SubtitleTrack) -> list[RawCue]:
        url = track.url
        if url.startswith("//"):
            url = "https:" + url
        try:
            resp = self._client.get(url, headers={"Referer": "https://www.bilibili.com/"})
            resp.raise_for_status()
            body = resp.json()
        except Exception as exc:
            raise ImportFailed("SUBTITLE_FETCH_FAILED", f"字幕文件下载失败：{exc}", 502) from exc
        cues: list[RawCue] = []
        for item in body.get("body") or []:
            start = int(round(float(item.get("from", 0)) * 1000))
            end = int(round(float(item.get("to", 0)) * 1000))
            text = str(item.get("content") or "").strip()
            if not text or end <= start:
                continue
            cues.append(RawCue(seq=len(cues) + 1, start_ms=start, end_ms=end, text=text))
        if not cues:
            raise ImportFailed("TRACK_NOT_AVAILABLE", "字幕轨为空或格式不可用", 422)
        return cues


def classify_failure(exc: Exception) -> ImportFailed:
    if isinstance(exc, ImportFailed):
        return exc
    return ImportFailed("BILIBILI_IMPORT_FAILED", f"B 站导入失败：{exc}", 500)
