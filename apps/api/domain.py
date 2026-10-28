"""Domain types shared by API, store and search layers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, detail: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.detail is not None:
            out["detail"] = self.detail
        return out


class BadSubtitle(AppError):
    def __init__(self, message: str, detail: Any = None):
        super().__init__("BAD_SUBTITLE", message, 422, detail)


class DatabaseUnavailable(AppError):
    def __init__(self, message: str):
        super().__init__("DB_UNAVAILABLE", message, 503)


class EmbeddingUnavailable(AppError):
    def __init__(self, message: str):
        super().__init__("EMBEDDING_UNAVAILABLE", message, 503)


class ImportFailed(AppError):
    pass


@dataclass
class RawCue:
    seq: int
    start_ms: int
    end_ms: int
    text: str


@dataclass
class ParsedSubtitle:
    cues: list[RawCue]
    warnings: list[str] = field(default_factory=list)
    skipped_empty: int = 0
    language: str = "zh"


@dataclass
class PassageDraft:
    start_ms: int
    end_ms: int
    text: str
    cue_start_seq: int
    cue_end_seq: int


@dataclass
class SearchHit:
    passage_id: str
    video_id: str
    course_id: str
    video_title: str
    course_name: str
    start_ms: int
    end_ms: int
    cue_start_seq: int
    cue_end_seq: int
    text: str
    source_url: str
    jump_url: str
    playback_capability: str
    match_reason: str
    score: float
    rank: int = 0
    lexical_score: float | None = None
    semantic_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "video_id": self.video_id,
            "course_id": self.course_id,
            "video_title": self.video_title,
            "course_name": self.course_name,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "cue_start_seq": self.cue_start_seq,
            "cue_end_seq": self.cue_end_seq,
            "text": self.text,
            "source_url": self.source_url,
            "jump_url": self.jump_url,
            "playback_capability": self.playback_capability,
            "match_reason": self.match_reason,
            "score": round(self.score, 6),
            "rank": self.rank,
            "lexical_score": None if self.lexical_score is None else round(self.lexical_score, 6),
            "semantic_score": None if self.semantic_score is None else round(self.semantic_score, 6),
        }
