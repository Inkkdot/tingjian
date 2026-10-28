"""Rebuild passages and real embeddings from stored cues, repeatably.

Use after changing chunking rules or the embedding model. The cue rows stay
untouched; only passages are regenerated. `--bump-version` advances the stored
index version first so repeated imports afterwards are treated as stale.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from embeddings import Embedder  # noqa: E402
from store import Store  # noqa: E402
from subtitles import chunk_passages  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild passages for stored lectures")
    parser.add_argument("--video-id", action="append", default=[], help="lecture id; repeatable")
    parser.add_argument("--skip-embeddings", action="store_true", help="rebuild text only")
    parser.add_argument("--bump-version", action="store_true", help="advance index_version first")
    parser.add_argument("--output", default="artifacts/reindex.json")
    args = parser.parse_args()

    store = Store()
    store.ensure_schema()
    if args.bump_version:
        version = int(store.meta().get("index_version", "1")) + 1
        store.set_meta("index_version", str(version))
        print(f"index_version -> {version}")

    videos = store.list_videos()
    if args.video_id:
        known = {v["id"] for v in videos}
        unknown = sorted(set(args.video_id) - known)
        if unknown:
            print("unknown video id:", ", ".join(unknown), file=sys.stderr)
            return 2
        wanted = set(args.video_id)
        videos = [v for v in videos if v["id"] in wanted]

    embedder = None
    if not args.skip_embeddings:
        embedder = Embedder()
        if not embedder.available():
            print(f"embedding unavailable, text-only rebuild: {embedder.error}", file=sys.stderr)

    results = []
    failed = 0
    for video in videos:
        cues = store.cues_raw(video["id"])
        drafts = chunk_passages(cues)
        vectors = None
        warning = None
        if embedder is not None and embedder.available():
            try:
                vectors = embedder.embed_passages([draft.text for draft in drafts])
            except Exception as exc:
                warning = f"{type(exc).__name__}: {exc}"[:300]
        count = store.rebuild_passages(
            video_id=video["id"], drafts=drafts, embeddings=vectors
        )
        result = {
            "video_id": video["id"],
            "cues": len(cues),
            "passages": count,
            "embedded": len(vectors) if vectors else 0,
            "warning": warning,
        }
        results.append(result)
        print(
            f"{video['id']}: cues={len(cues)} passages={count} embedded={result['embedded']}"
            + (f" warning={warning}" if warning else "")
        )
        if warning:
            failed += 1

    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "videos": results,
                "index_version": store.meta().get("index_version", "1"),
                "skip_embeddings": args.skip_embeddings,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("wrote", out)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
