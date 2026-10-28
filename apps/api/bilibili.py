"""Bilibili URL parsing, metadata and subtitle-track import.

Anonymous requests only see public tracks. When the operator supplies a
browser session (BILIBILI_COOKIE or BILIBILI_COOKIE_FILE, kept outside the
repo), the client also reads AI tracks via the wbi-signed player endpoint.
The cookie is never persisted, logged or returned to the frontend.

Unsigned ``/x/player/v2`` was observed returning unrelated subtitle tracks,
so signed requests are the default and parsed cues are checked against the
part duration before ingestion.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import httpx

from domain import ImportFailed, RawCue

API = "https://api.bilibili.com"
WBI_MIXIN_TAB = (
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
)
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
    def __init__(self, cookie: str = "", timeout: float = 12.0):
        self._client = httpx.Client(headers=HEADERS, timeout=timeout, follow_redirects=True)
        self._cookie = cookie.strip()
        self._guest_cookie = ""
        self._wbi_key = ""
        self._wbi_at = 0.0

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "BilibiliClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @property
    def authenticated(self) -> bool:
        return bool(self._cookie)

    def _ensure_guest_cookie(self) -> None:
        if self._cookie or self._guest_cookie:
            return
        try:
            resp = self._client.get(f"{API}/x/frontend/finger/spi")
            data = resp.json().get("data") or {}
            b3, b4 = data.get("b_3"), data.get("b_4")
            if b3:
                self._guest_cookie = f"buvid3={b3}; buvid4={b4 or ''}"
        except Exception:
            self._guest_cookie = ""

    def _ensure_wbi_key(self) -> str:
        if self._wbi_key and time.time() - self._wbi_at < 6 * 3600:
            return self._wbi_key
        try:
            payload = self._get_json("/x/web-interface/nav", {})
            wbi = (payload.get("data") or {}).get("wbi_img") or {}
            img_key = str(wbi.get("img_url") or "").rsplit("/", 1)[-1].split(".")[0]
            sub_key = str(wbi.get("sub_url") or "").rsplit("/", 1)[-1].split(".")[0]
            if not img_key or not sub_key:
                return ""
            raw = img_key + sub_key
            self._wbi_key = "".join(raw[i] for i in WBI_MIXIN_TAB if i < len(raw))[:32]
            self._wbi_at = time.time()
            return self._wbi_key
        except Exception:
            return ""

    def _wbi_query(self, params: dict[str, Any]) -> str:
        key = self._ensure_wbi_key()
        if not key:
            return ""
        merged = {**params, "wts": int(time.time())}
        query = "&".join(
            f"{quote(str(k), safe='')}={quote(str(v), safe='-_.~')}"
            for k, v in sorted(merged.items())
        )
        return f"{query}&w_rid={hashlib.md5((query + key).encode()).hexdigest()}"

    def _get_json(
        self, path: str, params: dict[str, Any] | None = None, query: str = ""
    ) -> dict[str, Any]:
        self._ensure_guest_cookie()
        cookie = self._cookie or self._guest_cookie
        headers = {"Cookie": cookie} if cookie else {}
        url = f"{API}{path}"
        if query:
            url = f"{url}?{query}"
        try:
            resp = self._client.get(url, params=params, headers=headers)
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
        query = self._wbi_query({"bvid": bvid, "cid": cid})
        payload: dict[str, Any] | None = None
        if query:
            try:
                payload = self._get_json("/x/player/wbi/v2", query=query)
            except ImportFailed:
                payload = None
        if payload is None:
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
        cues.sort(key=lambda cue: cue.start_ms)
        for index, cue in enumerate(cues, start=1):
            cue.seq = index
        return cues


def validate_track(cues: list[RawCue], duration_ms: int) -> dict[str, Any]:
    """Reject tracks whose timeline cannot belong to this part.

    Unsigned player responses were observed carrying subtitles from unrelated
    videos, so a successful HTTP call is not enough to trust the payload.
    """
    if not cues:
        raise ImportFailed("TRACK_NOT_AVAILABLE", "字幕轨为空或格式不可用", 422)
    last_end = max(cue.end_ms for cue in cues)
    speech_ms = sum(cue.end_ms - cue.start_ms for cue in cues)
    report = {
        "cue_count": len(cues),
        "last_end_ms": last_end,
        "speech_ms": speech_ms,
        "duration_ms": duration_ms,
        "coverage": round(last_end / duration_ms, 3) if duration_ms > 0 else None,
    }
    if duration_ms <= 0:
        return report
    if last_end > duration_ms * 1.05:
        raise ImportFailed(
            "TRACK_MISMATCH",
            "字幕时间轴超出视频时长，B 站可能返回了错误的字幕轨。请重试，或导出 SRT 后上传。",
            422,
            report,
        )
    if last_end < duration_ms * 0.5 or speech_ms < duration_ms * 0.1:
        raise ImportFailed(
            "TRACK_MISMATCH",
            "字幕覆盖范围与视频时长明显不符，B 站可能返回了错误的字幕轨。请重试，或导出 SRT 后上传。",
            422,
            report,
        )
    return report


def classify_failure(exc: Exception) -> ImportFailed:
    if isinstance(exc, ImportFailed):
        return exc
    return ImportFailed("BILIBILI_IMPORT_FAILED", f"B 站导入失败：{exc}", 500)
