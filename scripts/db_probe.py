"""Real seekdb capability probe. Writes artifacts/db-probe.json."""
from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
sys.path.insert(0, str(ROOT / "apps" / "api"))

from config import settings  # noqa: E402


def main() -> int:
    ARTIFACTS.mkdir(exist_ok=True)
    report: dict = {
        "python": sys.version,
        "platform": platform.platform(),
        "connection": {
            "host": settings.db_host,
            "port": settings.db_port,
            "user": settings.db_user,
            "database": settings.db_name,
        },
        "checks": [],
    }
    ok = True
    conn = None
    try:
        conn = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )
        cur = conn.cursor()
        cur.execute("SELECT VERSION() AS v")
        report["version"] = cur.fetchone()["v"]
        cur.execute("CREATE DATABASE IF NOT EXISTS tingjian_probe")
        cur.execute("USE tingjian_probe")
        cur.execute("DROP TABLE IF EXISTS probe_fts")
        cur.execute(
            """
            CREATE TABLE probe_fts (
              id INT PRIMARY KEY AUTO_INCREMENT,
              content TEXT,
              embedding VECTOR(4),
              FULLTEXT KEY ft (content) WITH PARSER ik,
              VECTOR KEY vec (embedding) WITH (DISTANCE=COSINE, TYPE=HNSW, LIB=VSAG)
            ) DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute(
            "INSERT INTO probe_fts(content, embedding) VALUES"
            "('数据库事务的隔离性保证并发执行正确','[0.1,0.2,0.3,0.4]'),"
            "('索引可以加速查询但会增加写入成本','[0.4,0.3,0.2,0.1]'),"
            "('事务的原子性要求全部成功或全部回滚','[0.2,0.2,0.4,0.2]')"
        )
        cur.execute("SELECT COUNT(*) AS n FROM probe_fts")
        rows = cur.fetchone()["n"]
        report["checks"].append({"name": "create/insert/select", "ok": rows == 3, "rows": rows})
        cur.execute(
            "SELECT id, MATCH(content) AGAINST('隔离性') AS s FROM probe_fts "
            "WHERE MATCH(content) AGAINST('隔离性')"
        )
        fts = cur.fetchall()
        report["checks"].append(
            {"name": "fulltext ik chinese", "ok": bool(fts), "hits": fts, "term": "隔离性"}
        )
        cur.execute(
            "SELECT id, cosine_distance(embedding,'[0.1,0.2,0.3,0.4]') AS d "
            "FROM probe_fts ORDER BY d LIMIT 3"
        )
        vec = cur.fetchall()
        report["checks"].append(
            {"name": "vector cosine distance", "ok": bool(vec), "hits": vec}
        )
        cur.execute("SHOW CREATE TABLE probe_fts")
        ddl = list(cur.fetchone().values())[1]
        report["ddl"] = ddl
        report["checks"].append(
            {
                "name": "fulltext + vector indexes coexist",
                "ok": "FULLTEXT KEY" in ddl and "VECTOR KEY" in ddl,
            }
        )
        cur.execute("DROP TABLE IF EXISTS probe_fts")
    except Exception as exc:
        ok = False
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if conn:
            conn.close()
    for check in report.get("checks", []):
        ok = ok and bool(check["ok"])
    report["ok"] = ok
    report["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (ARTIFACTS / "db-probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
