"""Hybrid retrieval: seekdb lexical + real-vector recall, then RRF fusion."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from domain import SearchHit
from embeddings import Embedder
from playback import jump_for
from store import Store

STOPWORDS = {
    "什么", "怎么", "如何", "为什么", "哪些", "哪个", "可以", "需要", "一个",
    "我们", "你们", "他们", "这个", "那个", "以及", "还是", "就是", "因为",
    "所以", "如果", "那么", "时候", "进行", "通过", "使用", "实现", "作用",
    "原理", "过程", "主要", "介绍", "讨论", "要求", "包括", "比如", "例如",
}


def query_keywords(query: str) -> list[str]:
    import jieba

    for word in (
        "原子性", "一致性", "隔离性", "持久性", "隔离级别", "脏读", "幻读",
        "不可重复读", "间隙锁", "快照读", "两阶段提交", "分布式事务",
        "B+树", "聚簇索引", "二级索引", "回表", "覆盖索引", "最左前缀",
        "联合索引", "索引下推", "页分裂", "执行计划", "嵌套循环", "哈希连接",
        "排序合并", "谓词下推", "分区裁剪", "慢查询", "统计信息",
        "进程控制块", "上下文切换", "用户级线程", "内核级线程", "协程",
        "优先级反转", "竞态条件", "互斥锁", "信号量", "银行家算法",
        "虚拟内存", "页表", "缺页中断", "页面置换", "工作集", "写时复制",
        "内存映射", "伙伴系统", "段页式", "TLB", "LRU", "EXPLAIN",
    ):
        jieba.add_word(word)
    terms: list[str] = []
    for raw in jieba.cut_for_search(query):
        term = raw.strip().lower()
        if len(term) < 2 or term in STOPWORDS:
            continue
        if not re.search(r"[0-9a-z\u4e00-\u9fff]", term):
            continue
        if term not in terms:
            terms.append(term)
    return terms


def filter_lexical(rows: list[dict[str, Any]], terms: list[str]) -> list[dict[str, Any]]:
    """Keep candidates that contain at least half of the query keywords.

    seekdb's ik parser uses OR semantics in natural-language mode, so common
    tokens can pull in every passage. The application-side coverage filter keeps
    the database recall but removes candidates without enough real term overlap.
    """
    if not terms:
        return []
    needed = max(1, (len(terms) + 1) // 2)
    kept = []
    for row in rows:
        text = (row.get("text") or "").lower()
        matched = sum(1 for term in terms if term.lower() in text)
        if matched >= needed:
            row["matched_terms"] = matched
            kept.append(row)
    return kept


def _semantic_gate() -> float:
    try:
        return float(os.getenv("TINGJIAN_MIN_SEMANTIC", "0.49"))
    except ValueError:
        return 0.49


@dataclass
class SearchOutcome:
    hits: list[SearchHit]
    mode: str
    lexical_candidates: int = 0
    semantic_candidates: int = 0
    rrf_k: int = 60
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": None,
            "mode": self.mode,
            "rrf_k": self.rrf_k,
            "candidate_counts": {
                "lexical": self.lexical_candidates,
                "semantic": self.semantic_candidates,
            },
            "hits": [h.to_dict() for h in self.hits],
            "warnings": self.warnings,
        }


def _row_to_hit(
    row: dict[str, Any],
    *,
    score: float,
    reason: str,
    lexical: float | None = None,
    semantic: float | None = None,
) -> SearchHit:
    jump_url, capability = jump_for(
        platform=str(row.get("platform") or ""),
        source_url=str(row.get("source_url") or ""),
        platform_video_id=str(row.get("platform_video_id") or ""),
        part_index=int(row.get("part_index") or 1),
        start_ms=int(row["start_ms"]),
        offset_ms=int(row.get("offset_ms") or 0),
    )
    return SearchHit(
        passage_id=row["passage_id"],
        video_id=row["video_id"],
        course_id=row["course_id"],
        video_title=row["video_title"],
        course_name=row["course_name"],
        start_ms=int(row["start_ms"]),
        end_ms=int(row["end_ms"]),
        cue_start_seq=int(row["cue_start_seq"]),
        cue_end_seq=int(row["cue_end_seq"]),
        text=row["text"],
        source_url=row.get("source_url") or "",
        jump_url=jump_url,
        playback_capability=capability,
        match_reason=reason,
        score=score,
        lexical_score=lexical,
        semantic_score=semantic,
    )


def _overlap_ratio(a: SearchHit, b: SearchHit) -> float:
    inter = max(0, min(a.end_ms, b.end_ms) - max(a.start_ms, b.start_ms))
    shortest = min(a.end_ms - a.start_ms, b.end_ms - b.start_ms)
    if shortest <= 0:
        return 0.0
    return inter / shortest


def dedupe_overlaps(hits: list[SearchHit], threshold: float = 0.6) -> list[SearchHit]:
    kept: list[SearchHit] = []
    for hit in sorted(hits, key=lambda h: h.score, reverse=True):
        if any(
            hit.video_id == other.video_id and _overlap_ratio(hit, other) >= threshold
            for other in kept
        ):
            continue
        kept.append(hit)
    return kept


def search(
    store: Store,
    embedder: Embedder,
    query: str,
    *,
    limit: int = 5,
    course_id: str | None = None,
    mode: str = "hybrid",
    rrf_k: int = 60,
    candidate_limit: int | None = None,
) -> SearchOutcome:
    query = query.strip()
    if not query:
        return SearchOutcome([], mode, rrf_k=rrf_k)
    fetch = candidate_limit or max(20, limit * 8)
    lexical_rows: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    terms = query_keywords(query)

    if mode in ("lexical", "hybrid"):
        lexical_rows = store.search_lexical(query, fetch, course_id)
        if terms:
            lexical_rows = filter_lexical(lexical_rows, terms)
    if mode in ("semantic", "hybrid"):
        try:
            vector = embedder.embed_query(query)
            semantic_rows = store.search_semantic(vector, fetch, course_id)
        except Exception as exc:
            warnings.append(f"向量召回不可用：{str(exc)[:200]}")
            if mode == "semantic":
                return SearchOutcome([], "lexical_fallback", rrf_k=rrf_k, warnings=warnings)

    if semantic_rows and not lexical_rows:
        best = 1.0 - float(semantic_rows[0]["distance"])
        if best < _semantic_gate():
            warnings.append(
                f"无答案判定：最高语义相似度 {best:.3f} 低于阈值 {_semantic_gate():.2f}，返回空集"
            )
            semantic_rows = []

    if mode == "semantic" and not warnings:
        hits = [
            _row_to_hit(
                row,
                score=1.0 - float(row["distance"]),
                reason="语义召回",
                semantic=1.0 - float(row["distance"]),
            )
            for row in semantic_rows
        ]
        hits = dedupe_overlaps(hits)[:limit]
        for i, h in enumerate(hits, 1):
            h.rank = i
        return SearchOutcome(
            hits, "semantic", 0, len(semantic_rows), rrf_k=rrf_k, warnings=warnings
        )

    if mode == "lexical":
        hits = [
            _row_to_hit(
                row,
                score=float(row["lexical_score"]),
                reason="关键词命中",
                lexical=float(row["lexical_score"]),
            )
            for row in lexical_rows
        ]
        hits = dedupe_overlaps(hits)[:limit]
        for i, h in enumerate(hits, 1):
            h.rank = i
        return SearchOutcome(
            hits, "lexical", len(lexical_rows), 0, rrf_k=rrf_k, warnings=warnings
        )

    # RRF fusion
    fused: dict[str, dict[str, Any]] = {}
    for rank, row in enumerate(lexical_rows, 1):
        item = fused.setdefault(
            row["passage_id"], {"row": row, "rrf": 0.0, "lexical": None, "semantic": None}
        )
        item["rrf"] += 1.0 / (rrf_k + rank)
        item["lexical"] = float(row["lexical_score"])
    for rank, row in enumerate(semantic_rows, 1):
        item = fused.setdefault(
            row["passage_id"], {"row": row, "rrf": 0.0, "lexical": None, "semantic": None}
        )
        item["rrf"] += 1.0 / (rrf_k + rank)
        item["semantic"] = 1.0 - float(row["distance"])

    hits: list[SearchHit] = []
    for item in fused.values():
        row = item["row"]
        lex, sem = item["lexical"], item["semantic"]
        if lex is not None and sem is not None:
            reason = "关键词 + 语义共同命中"
        elif lex is not None:
            reason = "关键词命中"
        else:
            reason = "语义召回"
        hits.append(
            _row_to_hit(row, score=item["rrf"], reason=reason, lexical=lex, semantic=sem)
        )
    hits = dedupe_overlaps(hits)[:limit]
    for i, h in enumerate(hits, 1):
        h.rank = i
    return SearchOutcome(
        hits,
        "hybrid" if not warnings else "lexical_only",
        len(lexical_rows),
        len(semantic_rows),
        rrf_k=rrf_k,
        warnings=warnings,
    )
