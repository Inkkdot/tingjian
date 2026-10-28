"""FastAPI application for 「听见」."""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bilibili import (
    BilibiliClient,
    classify_failure,
    parse_bilibili_url,
    validate_track,
)
from config import settings
from domain import AppError, BadSubtitle, ImportFailed, RawCue
from embeddings import MODEL_LABEL, Embedder
from playback import bilibili_url, jump_for
from review import build_review_playlist
from search import search as run_search
from store import SCHEMA_VERSION, Store
from subtitles import chunk_passages, coverage_report, parse_subtitle, source_hash

BASE_DIR = Path(__file__).resolve().parents[2]
WEB_DIST = BASE_DIR / "apps" / "web" / "dist"

app = FastAPI(title="听见 TingJian", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = Store()
embedder = Embedder()


@app.exception_handler(AppError)
async def app_error_handler(_request, exc: AppError):
    return JSONResponse(status_code=exc.status, content=exc.to_dict())


class BilibiliImport(BaseModel):
    url: str
    course_id: str | None = None
    course_name: str | None = None
    term: str = ""
    part_index: int | None = None
    offset_ms: int = 0


class PlaylistRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    budget_ms: int = Field(gt=0, le=6 * 3600_000)
    title: str | None = None
    k: int = Field(default=20, ge=1, le=60)
    diversify: bool = True


def _slug(text: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", text).strip("-").lower()
    if not cleaned:
        cleaned = fallback
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:6]
    return f"{cleaned[:32]}-{digest}"


def _course(course_id: str | None, course_name: str | None, term: str) -> tuple[str, str]:
    name = (course_name or "").strip()
    cid = (course_id or "").strip()
    if not cid and not name:
        cid, name = "c-general", "未分类课程"
    if not cid:
        cid = _slug(name, "course")
    if not name:
        name = cid
    store.upsert_course(cid, name, term)
    return cid, name


def _embed(texts: list[str], warnings: list[str]) -> list[list[float]] | None:
    if not settings.embedding_enabled:
        warnings.append("真实 Embedding 已关闭（TINGJIAN_EMBEDDING=0）")
        return None
    try:
        return embedder.embed_passages(texts)
    except Exception as exc:
        warnings.append(f"Embedding 生成失败，已保留原始 cue，等待重建：{str(exc)[:200]}")
        return None


def _ingest_cues(
    *,
    cues: list[RawCue],
    course_id: str,
    course_name: str,
    term: str,
    title: str,
    source_url: str,
    source_type: str,
    platform: str,
    platform_video_id: str,
    part_index: int,
    cid: int | None,
    cover_url: str,
    subtitle_kind: str,
    duration_ms: int,
    offset_ms: int,
    language: str,
    warnings: list[str],
    force: bool = False,
) -> dict[str, Any]:
    drafts = chunk_passages(cues)
    report = coverage_report(cues, drafts)
    if report["missing_cues"]:
        raise BadSubtitle("切块未覆盖全部字幕", report)
    digest = source_hash(
        platform=platform,
        platform_video_id=platform_video_id,
        part_index=part_index,
        language=language,
        source_type=source_type,
        cues=cues,
    )
    vectors = _embed([d.text for d in drafts], warnings) if drafts else None
    video_seed = f"{platform}:{platform_video_id}:{part_index}"
    video_id = f"v-{hashlib.sha1(video_seed.encode()).hexdigest()[:14]}"
    result = store.ingest(
        course_id=course_id,
        course_name=course_name,
        term=term,
        video_id=video_id,
        title=title,
        source_url=source_url,
        source_type=source_type,
        platform=platform,
        platform_video_id=platform_video_id,
        part_index=part_index,
        cid=cid,
        cover_url=cover_url,
        subtitle_kind=subtitle_kind,
        duration_ms=duration_ms,
        offset_ms=offset_ms,
        language=language,
        cues=cues,
        passage_drafts=drafts,
        source_hash=digest,
        embeddings=vectors,
        warnings=warnings,
        force=force,
    )
    return {
        "video_id": result.video_id,
        "status": result.status,
        "cue_count": result.cue_count,
        "passage_count": result.passage_count,
        "embedded_count": result.embedded_count,
        "source_hash": result.source_hash,
        "warnings": result.warnings,
        "coverage": report,
        "course_id": course_id,
        "course_name": course_name,
    }


@app.on_event("startup")
def startup() -> None:
    try:
        store.ensure_schema()
    except Exception as exc:  # health reports the failure instead of crashing the UI
        print(f"[startup] seekdb unavailable: {exc}")


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        store.ensure_schema()
        counts = store.counts()
        ok = store.ping()
        err = None
    except Exception as exc:
        counts = {}
        ok = False
        err = str(exc)[:300]
    vector_ready = bool(counts.get("embedded_passages")) and embedder.available()
    meta = {}
    if ok:
        try:
            meta = store.meta()
        except Exception:
            meta = {}
    return {
        "mode": settings.mode,
        "store_ok": ok,
        "database": "seekdb",
        "database_version": "5.7.25-OceanBase seekdb-v1.4.0.0",
        "schema_version": SCHEMA_VERSION,
        "embedding_model": MODEL_LABEL if vector_ready else None,
        "embedding_error": embedder.error,
        "course_count": counts.get("courses", 0),
        "video_count": counts.get("videos", 0),
        "cue_count": counts.get("cues", 0),
        "passage_count": counts.get("passages", 0),
        "embedded_passage_count": counts.get("embedded_passages", 0),
        "error": err,
        "capabilities": {
            "lexical_search": bool(ok),
            "vector_search": bool(vector_ready),
            "hybrid_search": bool(ok and vector_ready),
            "bilibili_import": bool(ok and meta.get("bilibili_import_ok") == "1"),
            "bilibili_login": settings.bilibili_login_configured,
            "bilibili_browser_fallback": True,
            "review_playlist": True,
            "asr": False,
            "llm_summary": False,
        },
    }


@app.get("/api/courses")
def courses() -> dict[str, Any]:
    return {"courses": store.list_courses()}


@app.get("/api/videos")
def videos(course_id: str | None = None) -> dict[str, Any]:
    return {"videos": store.list_videos(course_id)}


@app.get("/api/videos/{video_id}/cues")
def video_cues(video_id: str) -> dict[str, Any]:
    cues = store.get_video_cues(video_id)
    if not cues:
        raise AppError("NOT_FOUND", "讲次不存在或没有字幕", 404)
    return {"video_id": video_id, "cues": cues}


@app.get("/api/search")
def api_search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(5, ge=1, le=20),
    course_id: str | None = None,
    mode: str = Query("hybrid", pattern="^(hybrid|lexical|semantic)$"),
    rrf_k: int = Query(60, ge=1, le=200),
) -> dict[str, Any]:
    outcome = run_search(
        store, embedder, q, limit=limit, course_id=course_id, mode=mode, rrf_k=rrf_k
    )
    payload = outcome.to_dict()
    payload["query"] = q
    payload["course_id"] = course_id
    return payload


@app.post("/api/import/bilibili")
def import_bilibili(payload: BilibiliImport) -> dict[str, Any]:
    parsed = parse_bilibili_url(payload.url)
    cid, cname = _course(payload.course_id, payload.course_name, payload.term)
    warnings: list[str] = []
    try:
        with BilibiliClient(cookie=settings.bilibili_cookie) as client:
            video = client.fetch_video(parsed["bvid"])
            part_index = payload.part_index or parsed["part_index"]
            part = next((p for p in video.parts if p.page == part_index), None)
            if part is None:
                raise ImportFailed(
                    "BAD_PART", f"视频只有 {len(video.parts)} P，找不到第 {part_index} P", 422
                )
            tracks = client.fetch_subtitles(video.bvid, part.cid)
            if not tracks:
                hint = (
                    "该视频没有可用字幕轨（登录态已生效）。请用「视频字幕提取器 Pro」"
                    "在浏览器导出 SRT 后上传。"
                    if client.authenticated
                    else "未发现字幕轨。配置本机 BILIBILI_COOKIE 可读取登录态字幕，"
                    "或用「视频字幕提取器 Pro」导出 SRT 后上传。"
                )
                raise ImportFailed(
                    "TRACK_NOT_AVAILABLE",
                    hint,
                    422,
                    {
                        "bvid": video.bvid,
                        "cid": part.cid,
                        "part_index": part_index,
                        "path": "track_checked",
                        "authenticated": client.authenticated,
                        "hint": "browser_srt_fallback",
                        "title": video.title,
                        "part_title": part.title,
                    },
                )
            track = next((t for t in tracks if t.lan.startswith("zh")), tracks[0])
            cues = client.fetch_cues(track)
            track_report = validate_track(cues, part.duration_ms or video.duration_ms)
    except AppError:
        raise
    except Exception as exc:
        raise classify_failure(exc) from exc

    store.set_meta("bilibili_import_ok", "1")
    result = _ingest_cues(
        cues=cues,
        course_id=cid,
        course_name=cname,
        term=payload.term,
        title=part.title or video.title,
        source_url=f"https://www.bilibili.com/video/{video.bvid}?p={part_index}",
        source_type="bilibili_track",
        platform="bilibili",
        platform_video_id=video.bvid,
        part_index=part_index,
        cid=part.cid,
        cover_url=video.pic,
        subtitle_kind=track.lan_doc or track.lan,
        duration_ms=part.duration_ms or video.duration_ms,
        offset_ms=payload.offset_ms,
        language="zh",
        warnings=warnings,
    )
    result["bilibili"] = {
        "bvid": video.bvid,
        "title": video.title,
        "part_title": part.title,
        "owner": video.owner,
        "path": "login_track" if client.authenticated else "public_track",
        "track": track.lan_doc,
        "coverage": track_report,
    }
    return result


@app.get("/api/bilibili/preview")
def bilibili_preview(url: str) -> dict[str, Any]:
    parsed = parse_bilibili_url(url)
    try:
        with BilibiliClient(cookie=settings.bilibili_cookie) as client:
            video = client.fetch_video(parsed["bvid"])
            part = next(
                (p for p in video.parts if p.page == parsed["part_index"]), video.parts[0]
            )
            tracks = client.fetch_subtitles(video.bvid, part.cid)
    except AppError:
        raise
    except Exception as exc:
        raise classify_failure(exc) from exc
    return {
        "bvid": video.bvid,
        "title": video.title,
        "owner": video.owner,
        "pic": video.pic,
        "duration_ms": video.duration_ms,
        "parts": [p.__dict__ for p in video.parts],
        "part_index": part.page,
        "part_title": part.title,
        "cid": part.cid,
        "subtitle_tracks": [t.__dict__ for t in tracks],
        "track_available": bool(tracks),
        "authenticated": client.authenticated,
        "fallback_hint": (
            None
            if tracks
            else (
                "该视频没有可用字幕轨（登录态已生效），请导出 SRT 后上传。"
                if client.authenticated
                else "未发现字幕轨。配置本机 BILIBILI_COOKIE 可读取登录态字幕，或导出 SRT 后上传。"
            )
        ),
    }


@app.post("/api/import/srt")
async def import_srt(
    file: UploadFile = File(...),
    course_id: str | None = Form(None),
    course_name: str | None = Form(None),
    term: str = Form(""),
    title: str = Form(""),
    source_url: str = Form(""),
    platform: str = Form(""),
    platform_video_id: str = Form(""),
    part_index: int = Form(1),
    language: str = Form("zh"),
    offset_ms: int = Form(0),
    video_title: str | None = Form(None),
    force: bool = Form(False),
) -> dict[str, Any]:
    raw = await file.read()
    warnings: list[str] = []
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = raw.decode("gb18030")
            warnings.append("文件不是 UTF-8，已按 GB18030 解码")
        except UnicodeDecodeError as exc:
            raise BadSubtitle("字幕编码无法识别，请转换为 UTF-8 后重试") from exc
    parsed = parse_subtitle(content, file.filename or "")
    warnings.extend(parsed.warnings)
    if parsed.skipped_empty:
        warnings.append(f"跳过 {parsed.skipped_empty} 条空字幕")
    cid, cname = _course(course_id, course_name, term)
    display_title = (video_title or title or file.filename or "未命名讲次").strip()
    if not platform:
        platform = "bilibili" if "bilibili.com" in source_url else ("local" if not source_url else "generic")
    if not platform_video_id:
        if platform == "bilibili":
            bv = re.search(r"(BV[0-9A-Za-z]{10})", source_url)
            platform_video_id = bv.group(1) if bv else _slug(display_title, "video")
        else:
            platform_video_id = _slug(f"{cid}:{display_title}", "video")
    duration = parsed.cues[-1].end_ms if parsed.cues else 0
    result = _ingest_cues(
        cues=parsed.cues,
        course_id=cid,
        course_name=cname,
        term=term,
        title=display_title,
        source_url=source_url,
        source_type="srt_upload",
        platform=platform,
        platform_video_id=platform_video_id,
        part_index=part_index,
        cid=None,
        cover_url="",
        subtitle_kind="uploaded_srt",
        duration_ms=duration,
        offset_ms=offset_ms,
        language=language or parsed.language,
        warnings=warnings,
        force=force,
    )
    result["filename"] = file.filename
    result["warnings"] = warnings
    return result


@app.post("/api/review/playlist")
def create_playlist(payload: PlaylistRequest) -> dict[str, Any]:
    result = build_review_playlist(
        store,
        embedder,
        topic=payload.topic,
        budget_ms=payload.budget_ms,
        k=payload.k,
        diversify=payload.diversify,
    )
    playlist_id = f"pl-{int(time.time())}-{hashlib.sha1(payload.topic.encode()).hexdigest()[:6]}"
    store.save_playlist(
        playlist_id,
        payload.title or f"{payload.topic} · 复习清单",
        payload.topic,
        payload.budget_ms,
        result["items"],
    )
    result["playlist_id"] = playlist_id
    result["title"] = payload.title or f"{payload.topic} · 复习清单"
    return result


@app.get("/api/playlists/{playlist_id}")
def get_playlist(playlist_id: str) -> dict[str, Any]:
    playlist = store.get_playlist(playlist_id)
    if not playlist:
        raise AppError("NOT_FOUND", "复习清单不存在", 404)
    for item in playlist["items"]:
        jump, capability = jump_for(
            platform=item["platform"],
            source_url=item["source_url"],
            platform_video_id=item["platform_video_id"],
            part_index=item["part_index"],
            start_ms=item["clip_start_ms"],
            offset_ms=item["offset_ms"],
        )
        item["jump_url"] = jump
        item["playback_capability"] = capability
        item["duration_ms"] = item["clip_end_ms"] - item["clip_start_ms"]
    return playlist


if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB_DIST / "index.html")

    @app.get("/{path:path}")
    def spa(path: str):
        target = WEB_DIST / path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html")
