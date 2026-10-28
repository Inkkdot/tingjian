"""SRT / VTT parsing, validation and passage chunking."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from domain import BadSubtitle, ParsedSubtitle, PassageDraft, RawCue

_TIME_RE = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})"
)


def _to_ms(match: re.Match[str]) -> int:
    ms = int(match.group("ms").ljust(3, "0"))
    return (
        int(match.group("h")) * 3600_000
        + int(match.group("m")) * 60_000
        + int(match.group("s")) * 1000
        + ms
    )


def _clean_text(lines: list[str]) -> str:
    text = " ".join(part.strip() for part in lines if part.strip())
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _build_cues(blocks: list[list[str]], fmt: str) -> ParsedSubtitle:
    cues: list[RawCue] = []
    warnings: list[str] = []
    skipped = 0
    index = 0
    previous_end = -1
    for raw in blocks:
        lines = [ln for ln in raw if ln.strip() != ""]
        if not lines:
            continue
        if fmt == "srt" and lines[0].strip().isdigit():
            declared = int(lines[0].strip())
            lines = lines[1:]
            if declared != index + 1:
                warnings.append(f"字幕编号不连续：声明 {declared}，实际第 {index + 1} 条")
        if not lines or "-->" not in lines[0]:
            warnings.append(f"跳过无时间轴区块（第 {index + 1} 条）")
            skipped += 1
            continue
        left, _, right = lines[0].partition("-->")
        lm = _TIME_RE.search(left)
        rm = _TIME_RE.search(right)
        if not lm or not rm:
            raise BadSubtitle("时间戳格式无法解析", {"line": lines[0], "index": index + 1})
        start_ms, end_ms = _to_ms(lm), _to_ms(rm)
        if start_ms < 0 or end_ms <= start_ms:
            raise BadSubtitle(
                "时间区间非法：要求 0 ≤ start < end",
                {"index": index + 1, "start_ms": start_ms, "end_ms": end_ms},
            )
        text = _clean_text(lines[1:])
        index += 1
        if not text:
            skipped += 1
            continue
        if start_ms < previous_end:
            warnings.append(f"字幕区间重叠：第 {index} 条开始早于上一条结束")
        previous_end = max(previous_end, end_ms)
        cues.append(RawCue(seq=len(cues) + 1, start_ms=start_ms, end_ms=end_ms, text=text))
    if not cues:
        raise BadSubtitle("字幕文件不含任何有效 cue", {"skipped_empty": skipped})
    return ParsedSubtitle(cues=cues, warnings=warnings, skipped_empty=skipped)


def parse_srt(content: str) -> ParsedSubtitle:
    if content.startswith("\ufeff"):
        content = content.lstrip("\ufeff")
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n{2,}", content.strip())
    return _build_cues([b.split("\n") for b in blocks], "srt")


def parse_vtt(content: str) -> ParsedSubtitle:
    if content.startswith("\ufeff"):
        content = content.lstrip("\ufeff")
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")
    if lines and lines[0].strip().upper().startswith("WEBVTT"):
        lines = lines[1:]
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        elif line.strip().upper().startswith(("NOTE", "STYLE", "REGION")):
            continue
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return _build_cues(blocks, "vtt")


def parse_subtitle(content: str, filename: str = "") -> ParsedSubtitle:
    name = filename.lower()
    if name.endswith(".vtt") or content.lstrip("\ufeff").startswith("WEBVTT"):
        return parse_vtt(content)
    return parse_srt(content)


def source_hash(
    *,
    platform: str,
    platform_video_id: str,
    part_index: int,
    language: str,
    source_type: str,
    cues: list[RawCue],
) -> str:
    payload: dict[str, Any] = {
        "cues": [
            {"seq": c.seq, "start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text.strip()}
            for c in cues
        ],
        "language": language,
        "part_index": part_index,
        "platform": platform,
        "platform_video_id": platform_video_id,
        "source_type": source_type,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def chunk_passages(
    cues: list[RawCue],
    *,
    min_ms: int = 20_000,
    max_ms: int = 45_000,
    max_chars: int = 260,
    overlap_cues: int = 1,
) -> list[PassageDraft]:
    """Chunk cues into 20-45s windows; every non-empty cue is covered."""
    if not cues:
        return []
    ordered = sorted(cues, key=lambda c: c.seq)
    drafts: list[PassageDraft] = []
    n = len(ordered)
    i = 0
    while i < n:
        start = ordered[i]
        j = i
        chars = 0
        while j < n:
            cue = ordered[j]
            next_chars = chars + len(cue.text)
            duration = cue.end_ms - start.start_ms
            if j > i and (duration > max_ms or next_chars > max_chars):
                break
            chars = next_chars
            j += 1
        window = ordered[i:j]
        if not window:
            window = [start]
            j = i + 1
        text = "".join(c.text for c in window)
        drafts.append(
            PassageDraft(
                start_ms=window[0].start_ms,
                end_ms=window[-1].end_ms,
                text=text,
                cue_start_seq=window[0].seq,
                cue_end_seq=window[-1].seq,
            )
        )
        if j >= n:
            break
        step = max(1, j - i - overlap_cues)
        i = i + step
    return drafts


def coverage_report(cues: list[RawCue], drafts: list[PassageDraft]) -> dict[str, Any]:
    covered: set[int] = set()
    for d in drafts:
        covered.update(range(d.cue_start_seq, d.cue_end_seq + 1))
    missing = [c.seq for c in cues if c.seq not in covered]
    return {
        "cue_count": len(cues),
        "passage_count": len(drafts),
        "covered_cues": len(covered),
        "missing_cues": missing,
        "duration_ms": sum(c.end_ms - c.start_ms for c in cues),
    }
