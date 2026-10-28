"""Export real seekdb content into the static demo fixture (no embeddings)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from store import Store  # noqa: E402


def main() -> int:
    store = Store()
    data = store.export_fixture(limit_videos=20)
    data["notice"] = (
        "Demo 数据由 Live 模式从真实 seekdb 导出；浏览器内仅做关键词过滤，"
        "不等同于 seekdb 全文 + 向量混合检索。"
    )
    data["counts"] = store.counts()
    metrics = ROOT / "artifacts" / "metrics.json"
    if metrics.exists():
        report = json.loads(metrics.read_text(encoding="utf-8"))
        data["eval_summary"] = {
            mode: {
                "hit_at_3": value["hit_at_3"],
                "answered": value["answered_queries"],
                "no_answer_refused": value["no_answer_refused"],
                "latency_ms_mean": value["latency_ms_mean"],
            }
            for mode, value in report["modes"].items()
        }
    out = ROOT / "apps" / "web" / "public" / "fixture.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(data['videos'])} lectures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
