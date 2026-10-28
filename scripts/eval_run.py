"""Run the labeled retrieval evaluation over real seekdb, three modes.

Labels are hand-annotated on the authored corpus: a target lecture and a cue
phrase. A Top-3 hit counts when it lands in the same lecture within +/-15s of
the labeled cue start. No-answer queries must return an empty result.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from config import settings  # noqa: E402
from embeddings import Embedder  # noqa: E402
from search import search as run_search  # noqa: E402
from store import Store  # noqa: E402

TOLERANCE_MS = 15_000

LABELS = [
    ("事务的原子性靠什么实现", "db-01", "撤销日志"),
    ("脏读是什么", "db-01", "脏读"),
    ("间隙锁的作用", "db-01", "间隙锁"),
    ("为什么数据库使用 B+ 树", "db-02", "多路平衡查找树"),
    ("什么是回表", "db-02", "回表"),
    ("最左前缀原则", "db-02", "最左前缀"),
    ("索引失效的常见原因", "db-02", "隐式类型转换"),
    ("如何查看执行计划", "db-03", "EXPLAIN"),
    ("哈希连接的过程", "db-03", "哈希连接"),
    ("进程和线程的区别", "os-04", "资源分配的基本单位"),
    ("死锁的四个条件", "os-04", "四个条件是互斥"),
    ("页面置换的 LRU 算法", "os-05", "最近最少使用"),
    ("转账时一半成功一半失败怎么办", "db-01", "要么全部成功"),
    ("数据库怎么避免读到别人还没提交的数据", "db-01", "脏读"),
    ("为什么二叉搜索树不适合做磁盘索引", "db-02", "二叉树每个节点"),
    ("多线程同时改一个变量为什么会出错", "os-04", "竞态条件"),
    ("内存不够时操作系统怎么腾地方", "os-05", "页面置换算法"),
    (None, None, None),
    (None, None, None),
    (None, None, None),
]
NO_ANSWER_QUERIES = ["红烧肉怎么做好吃", "量子纠缠的物理原理", "如何申请出国留学签证"]


def video_map() -> dict[str, str]:
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    cur = conn.cursor()
    cur.execute("SELECT id, platform_video_id FROM videos WHERE platform='local'")
    rows = {r["platform_video_id"]: r["id"] for r in cur.fetchall()}
    conn.close()
    return rows


def expected_start(store: Store, lecture_id: str, phrase: str) -> tuple[str, int] | None:
    videos = video_map()
    video_id = videos.get(lecture_id)
    if not video_id:
        return None
    for cue in store.get_video_cues(video_id):
        if phrase in cue["text"]:
            return video_id, int(cue["start_ms"])
    return None


def is_hit(hits, video_id: str, start_ms: int) -> bool:
    for hit in hits[:3]:
        if hit.video_id != video_id:
            continue
        if hit.start_ms - TOLERANCE_MS <= start_ms <= hit.end_ms + TOLERANCE_MS:
            return True
    return False


def main() -> int:
    store = Store()
    embedder = Embedder()
    queries = []
    for (query, lecture, phrase), no_answer in zip(LABELS, [False] * 17 + [True] * 3):
        item = {"query": query, "no_answer": no_answer}
        if not no_answer:
            target = expected_start(store, lecture, phrase)
            if not target:
                print("label target missing:", lecture, phrase)
                return 1
            item["expected_video_id"], item["expected_start_ms"] = target
            item["expected_phrase"] = phrase
        queries.append(item)
    for query, item in zip(NO_ANSWER_QUERIES, queries[-3:]):
        item["query"] = query

    report = {
        "corpus": {
            "courses": store.counts()["courses"],
            "videos": store.counts()["videos"],
            "cues": store.counts()["cues"],
            "passages": store.counts()["passages"],
        },
        "annotation": {
            "total_queries": len(queries),
            "no_answer": 3,
            "tolerance_ms": TOLERANCE_MS,
            "hit_rule": "Top3 contains same lecture within +/-15s of labeled cue start",
        },
        "modes": {},
    }
    for mode in ("lexical", "semantic", "hybrid"):
        rows = []
        hits_at_3 = 0
        refusals = 0
        latencies = []
        run_search(store, embedder, queries[0]["query"], limit=5, mode=mode)  # warm up caches
        for item in queries:
            started = time.perf_counter()
            outcome = run_search(store, embedder, item["query"], limit=5, mode=mode)
            latencies.append((time.perf_counter() - started) * 1000)
            if item["no_answer"]:
                refused = len(outcome.hits) == 0
                refusals += int(refused)
                rows.append(
                    {
                        "query": item["query"],
                        "no_answer": True,
                        "refused": refused,
                        "hit_count": len(outcome.hits),
                        "warnings": outcome.warnings,
                    }
                )
            else:
                hit = is_hit(outcome.hits, item["expected_video_id"], item["expected_start_ms"])
                hits_at_3 += int(hit)
                rows.append(
                    {
                        "query": item["query"],
                        "no_answer": False,
                        "hit_at_3": hit,
                        "expected_video_id": item["expected_video_id"],
                        "expected_start_ms": item["expected_start_ms"],
                        "top3": [
                            {
                                "video_id": h.video_id,
                                "start_ms": h.start_ms,
                                "end_ms": h.end_ms,
                                "reason": h.match_reason,
                                "score": h.score,
                            }
                            for h in outcome.hits[:3]
                        ],
                        "warnings": outcome.warnings,
                    }
                )
        answered = len(queries) - 3
        report["modes"][mode] = {
            "answered_queries": answered,
            "hit_at_3": hits_at_3,
            "hit_at_3_rate": round(hits_at_3 / answered, 4),
            "no_answer_queries": 3,
            "no_answer_refused": refusals,
            "no_answer_rate": round(refusals / 3, 4),
            "latency_ms_mean": round(statistics.mean(latencies), 1),
            "latency_ms_p95": round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 1),
            "latency_ms_max": round(max(latencies), 1),
            "rows": rows,
        }

    out = ROOT / "artifacts" / "metrics.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'mode':10} {'Hit@3':>10} {'NoAnswer':>10} {'mean ms':>9}")
    for mode, data in report["modes"].items():
        print(
            f"{mode:10} {data['hit_at_3']}/{data['answered_queries']:<8} "
            f"{data['no_answer_refused']}/3{'':>6} {data['latency_ms_mean']:>8}"
        )
    print("\nfailures:")
    for mode, data in report["modes"].items():
        for row in data["rows"]:
            if row["no_answer"] and not row["refused"]:
                print(f"  [{mode}] false positive: {row['query']} ({row['hit_count']} hits)")
            if not row["no_answer"] and not row["hit_at_3"]:
                print(f"  [{mode}] miss: {row['query']}")
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
