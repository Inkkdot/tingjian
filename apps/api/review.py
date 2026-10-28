"""P2 review playlist: relevance + coverage greedy under a hard time budget."""
from __future__ import annotations

import math
from typing import Any

from embeddings import Embedder
from search import search as run_search
from store import Store


def _bigrams(text: str) -> set[str]:
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _union_length(ranges: list[tuple[int, int]]) -> int:
    total = 0
    cur_start = cur_end = None
    for start, end in sorted(ranges):
        if cur_start is None:
            cur_start, cur_end = start, end
        elif start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            total += cur_end - cur_start
            cur_start, cur_end = start, end
    if cur_start is not None:
        total += cur_end - cur_start
    return total


def build_review_playlist(
    store: Store,
    embedder: Embedder,
    *,
    topic: str,
    budget_ms: int,
    k: int = 20,
    diversify: bool = True,
) -> dict[str, Any]:
    outcome = run_search(store, embedder, topic, limit=k, mode="hybrid")
    recall = outcome.hits
    candidates = recall
    if recall:
        max_lex = max((hit.lexical_score or 0.0) for hit in recall)
        max_sem = max((hit.semantic_score or 0.0) for hit in recall)
        # Keep only passages with real topic overlap or strong semantics. Hybrid
        # recall intentionally casts wide; a review playlist should not fill the
        # budget with unrelated lectures that only share common words.
        candidates = [
            hit
            for hit in recall
            if (hit.lexical_score or 0.0) >= max(0.25, max_lex * 0.35)
            or (hit.semantic_score or 0.0) >= 0.45
        ]
    selected: list[dict[str, Any]] = []
    covered: set[str] = set()
    used_videos: dict[str, int] = {}
    used_ranges: dict[str, list[tuple[int, int]]] = {}
    total = 0
    remaining = budget_ms

    max_lex = max((hit.lexical_score or 0.0) for hit in candidates) if candidates else 1.0
    max_sem = max((hit.semantic_score or 0.0) for hit in candidates) if candidates else 1.0

    def relevance(hit: Any) -> float:
        lex = (hit.lexical_score or 0.0) / max(max_lex, 1e-9)
        sem = (hit.semantic_score or 0.0) / max(max_sem, 1e-9)
        return 0.55 * lex + 0.45 * sem

    scored: list[tuple[float, Any, set[str]]] = []
    for hit in candidates:
        terms = _bigrams(hit.text)
        novelty = len(terms - covered) / max(1, len(terms))
        penalty = 0.08 * used_videos.get(hit.video_id, 0) if diversify else 0.0
        scored.append((relevance(hit) * (0.9 + 0.1 * novelty) - penalty, hit, terms))

    while scored and len(selected) < k and remaining > 3000:
        scored.sort(key=lambda item: item[0], reverse=True)
        score, hit, terms = scored.pop(0)
        overlap = 0
        for start, end in used_ranges.get(hit.video_id, []):
            overlap += max(0, min(end, hit.end_ms) - max(start, hit.start_ms))
        clip_start = hit.start_ms
        clip_end = min(hit.end_ms, clip_start + max(3000, remaining + overlap))
        clip_duration = clip_end - clip_start
        if clip_duration <= 0:
            continue
        if overlap > clip_duration * 0.5:
            continue
        if clip_duration - overlap > remaining:
            continue
        reason_bits = [hit.match_reason]
        if overlap > 0:
            reason_bits.append("与已选片段同视频，重叠部分不重复计时")
        selected.append(
            {
                "passage_id": hit.passage_id,
                "rank": len(selected) + 1,
                "clip_start_ms": clip_start,
                "clip_end_ms": clip_end,
                "reason": "；".join(reason_bits),
                "video_id": hit.video_id,
                "course_id": hit.course_id,
                "video_title": hit.video_title,
                "course_name": hit.course_name,
                "text": hit.text,
                "start_ms": hit.start_ms,
                "end_ms": hit.end_ms,
                "score": hit.score,
            }
        )
        used_videos[hit.video_id] = used_videos.get(hit.video_id, 0) + 1
        used_ranges.setdefault(hit.video_id, []).append((clip_start, clip_end))
        total = sum(_union_length(ranges) for ranges in used_ranges.values())
        remaining = budget_ms - total
        covered |= terms
        rescored: list[tuple[float, Any, set[str]]] = []
        for old_score, cand, cand_terms in scored:
            novelty = len(cand_terms - covered) / max(1, len(cand_terms))
            penalty = 0.08 * used_videos.get(cand.video_id, 0) if diversify else 0.0
            rescored.append((relevance(cand) * (0.9 + 0.1 * novelty) - penalty, cand, cand_terms))
        scored = rescored

    courses = {item["course_id"] for item in selected}
    return {
        "topic": topic,
        "budget_ms": budget_ms,
        "total_duration_ms": total,
        "within_budget": total <= budget_ms,
        "course_coverage": len(courses),
        "candidate_count": len(candidates),
        "recall_count": len(recall),
        "algorithm": "relevance-first coverage greedy (interval merge, no MMR claim)",
        "warnings": outcome.warnings,
        "items": selected,
    }
