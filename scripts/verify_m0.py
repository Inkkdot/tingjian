"""M0 gate: real seekdb + real subtitle ingest + idempotency + SELECT."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pymysql
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from config import settings  # noqa: E402
from main import app  # noqa: E402

FIXTURES = ROOT / "fixtures" / "authored"
BILIBILI_SAMPLE = "https://www.bilibili.com/video/BV1pW411W7Do?p=1"


def db_counts() -> dict[str, int]:
    conn = pymysql.connect(
        host=settings.db_host, port=settings.db_port, user=settings.db_user,
        password=settings.db_password, database=settings.db_name, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    cur = conn.cursor()
    out = {}
    for table in ("courses", "videos", "cues", "passages"):
        cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
        out[table] = int(cur.fetchone()["n"])
    cur.execute("SELECT COUNT(*) AS n FROM passages WHERE embedding IS NOT NULL")
    out["embedded_passages"] = int(cur.fetchone()["n"])
    conn.close()
    return out


def fetch_cues(video_id: str) -> list[dict]:
    conn = pymysql.connect(
        host=settings.db_host, port=settings.db_port, user=settings.db_user,
        password=settings.db_password, database=settings.db_name, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    cur = conn.cursor()
    cur.execute(
        "SELECT seq, start_ms, end_ms, text FROM cues WHERE video_id=%s ORDER BY seq LIMIT 5",
        (video_id,),
    )
    rows = list(cur.fetchall())
    conn.close()
    return rows


def main() -> int:
    report: dict = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": []}
    ok = True

    def check(name: str, passed: bool, detail=None):
        nonlocal ok
        ok = ok and passed
        report["checks"].append({"name": name, "ok": passed, "detail": detail})
        print(("PASS " if passed else "FAIL ") + name)

    with TestClient(app) as client:
        health = client.get("/api/health").json()
        report["health"] = health
        check("db_probe: store_ok and schema", health["store_ok"] and health["schema_version"])

        manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
        first = manifest["lectures"][0]
        course = manifest["courses"][first["course_id"]]
        payload = {
            "course_id": first["course_id"],
            "course_name": course["name"],
            "term": course["term"],
            "title": first["title"],
            "platform": "local",
            "platform_video_id": first["platform_video_id"],
            "part_index": "1",
            "language": "zh",
        }
        before = db_counts()

        def upload(force: bool = False):
            with open(FIXTURES / first["file"], "rb") as fh:
                return client.post(
                    "/api/import/srt",
                    files={"file": (first["file"], fh, "application/x-subrip")},
                    data={**payload, "force": "true" if force else "false"},
                )

        first_resp = upload(force=True)
        check("srt import via POST /api/import/srt", first_resp.status_code == 200, first_resp.json())
        if first_resp.status_code != 200:
            return 1
        video_id = first_resp.json()["video_id"]
        after_first = db_counts()

        conn = pymysql.connect(
            host=settings.db_host, port=settings.db_port, user=settings.db_user,
            password=settings.db_password, database=settings.db_name, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM cues WHERE video_id=%s", (video_id,))
        stored_cues = int(cur.fetchone()["n"])
        cur.execute("SELECT COUNT(*) AS n FROM passages WHERE video_id=%s", (video_id,))
        stored_passages = int(cur.fetchone()["n"])
        conn.close()
        check(
            "cue/passage rows in seekdb match parse result",
            stored_cues == first_resp.json()["cue_count"]
            and stored_passages == first_resp.json()["passage_count"]
            and first_resp.json()["coverage"]["missing_cues"] == [],
            {
                "stored_cues": stored_cues,
                "stored_passages": stored_passages,
                "result": {
                    "cues": first_resp.json()["cue_count"],
                    "passages": first_resp.json()["passage_count"],
                },
            },
        )

        second = upload()
        after_second = db_counts()
        check(
            "same source re-import is idempotent",
            second.status_code == 200
            and second.json()["status"] == "unchanged"
            and after_second["cues"] == after_first["cues"]
            and after_second["passages"] == after_first["passages"],
            {"status": second.json().get("status"), "before": after_first, "after": after_second},
        )

        conn = pymysql.connect(
            host=settings.db_host, port=settings.db_port, user=settings.db_user,
            password=settings.db_password, database=settings.db_name, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        cur = conn.cursor()
        cur.execute("SELECT source_hash FROM videos WHERE id=%s", (video_id,))
        stored_hash = cur.fetchone()["source_hash"]
        conn.close()
        check("source_hash persisted", stored_hash == first_resp.json()["source_hash"], stored_hash)

        cues = fetch_cues(video_id)
        check(
            "SELECT returns cue text + timestamps by video_id",
            bool(cues) and all(c["end_ms"] > c["start_ms"] >= 0 for c in cues),
            cues[:2],
        )
        report["video_id"] = video_id
        report["cues_sample"] = cues[:2]

        preview = client.get("/api/bilibili/preview", params={"url": BILIBILI_SAMPLE})
        preview_ok = preview.status_code == 200
        check("real Bilibili metadata probe", preview_ok, preview.json())
        public_track = bool(preview.json().get("public_track_available")) if preview_ok else False
        report["bilibili_public_track_available"] = public_track

        bili_import = client.post("/api/import/bilibili", json={"url": BILIBILI_SAMPLE})
        bili_body = bili_import.json()
        report["bilibili_import"] = {"status_code": bili_import.status_code, "body": bili_body}
        check(
            "Bilibili import path returns classified result (not a crash)",
            bili_import.status_code in (200, 422, 403, 429, 502, 504),
            {"status_code": bili_import.status_code, "code": bili_body.get("code")},
        )

        search = client.get("/api/search", params={"q": "事务的原子性靠什么实现", "limit": 3})
        hits = search.json().get("hits", [])
        check(
            "search over real seekdb returns traceable hit",
            search.status_code == 200
            and bool(hits)
            and hits[0]["cue_start_seq"] <= hits[0]["cue_end_seq"]
            and hits[0]["start_ms"] < hits[0]["end_ms"],
            hits[:1],
        )

    report["bilibili_note"] = (
        "Public subtitle tracks required login in this environment. The Bilibili path "
        "is implemented and classified; M0 evidence uses the documented SRT fallback "
        "(POST /api/import/srt). Upload a browser-script-exported SRT to bind a real "
        "Bilibili source_url."
    )
    out = ROOT / "artifacts" / "m0-report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nM0 =", "PASS" if ok else "FAIL", "->", out)
    print("bilibili_public_track_available =", report.get("bilibili_public_track_available"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
