"""Import all self-authored SRT fixtures through the real HTTP API."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from main import app  # noqa: E402

FIXTURES = ROOT / "fixtures" / "authored"


def main() -> int:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    courses = manifest["courses"]
    results = []
    with TestClient(app) as client:
        for lecture in manifest["lectures"]:
            course = courses[lecture["course_id"]]
            with open(FIXTURES / lecture["file"], "rb") as fh:
                resp = client.post(
                    "/api/import/srt",
                    files={"file": (lecture["file"], fh, "application/x-subrip")},
                    data={
                        "course_id": lecture["course_id"],
                        "course_name": course["name"],
                        "term": course["term"],
                        "title": lecture["title"],
                        "source_url": lecture.get("source_url", ""),
                        "platform": lecture.get("platform", "local"),
                        "platform_video_id": lecture.get("platform_video_id", ""),
                        "part_index": str(lecture.get("part_index", 1)),
                        "language": lecture.get("language", "zh"),
                    },
                )
            body = resp.json()
            print(lecture["id"], resp.status_code, body.get("status"), body.get("cue_count"), body.get("passage_count"))
            results.append({"lecture": lecture["id"], "status_code": resp.status_code, "body": body})
            if resp.status_code != 200:
                print(json.dumps(body, ensure_ascii=False, indent=2))
                return 1
    out = ROOT / "artifacts" / "fixture-import.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
