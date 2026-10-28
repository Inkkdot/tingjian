"""seekdb (MySQL protocol) schema, idempotent ingest and query primitives."""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import pymysql
from pymysql.cursors import DictCursor

from config import settings
from domain import DatabaseUnavailable, RawCue
from embeddings import DIMENSION, MODEL_LABEL

SCHEMA_VERSION = "1"
CHUNK_VERSION = "2026-10-28.p1"


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"


@dataclass
class IngestResult:
    video_id: str
    status: str
    cue_count: int
    passage_count: int
    source_hash: str
    embedded_count: int
    warnings: list[str]


class Store:
    def __init__(self) -> None:
        self._schema_ready = False

    # ---------- connections ----------
    def _connect(self, with_db: bool = True) -> pymysql.connections.Connection:
        try:
            return pymysql.connect(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name if with_db else None,
                charset="utf8mb4",
                autocommit=True,
                cursorclass=DictCursor,
                connect_timeout=8,
                read_timeout=60,
                write_timeout=60,
            )
        except Exception as exc:
            raise DatabaseUnavailable(f"seekdb 连接失败：{exc}") from exc

    @contextmanager
    def cursor(self) -> Iterator[DictCursor]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                yield cur
        finally:
            conn.close()

    def ping(self) -> bool:
        try:
            with self.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                return cur.fetchone()["ok"] == 1
        except Exception:
            return False

    # ---------- schema ----------
    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        conn = self._connect(with_db=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}` "
                    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
                )
                cur.execute(f"USE `{settings.db_name}`")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS meta (
                      k VARCHAR(64) PRIMARY KEY,
                      v TEXT NOT NULL
                    ) DEFAULT CHARSET=utf8mb4
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS courses (
                      id VARCHAR(48) PRIMARY KEY,
                      name VARCHAR(200) NOT NULL,
                      term VARCHAR(64) NOT NULL DEFAULT '',
                      created_at BIGINT NOT NULL
                    ) DEFAULT CHARSET=utf8mb4
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS videos (
                      id VARCHAR(64) PRIMARY KEY,
                      course_id VARCHAR(48) NOT NULL,
                      title VARCHAR(300) NOT NULL,
                      source_url VARCHAR(1024) NOT NULL DEFAULT '',
                      source_type VARCHAR(24) NOT NULL,
                      platform VARCHAR(24) NOT NULL,
                      platform_video_id VARCHAR(64) NOT NULL DEFAULT '',
                      part_index INT NOT NULL DEFAULT 1,
                      cid BIGINT NULL,
                      subtitle_kind VARCHAR(32) NOT NULL DEFAULT '',
                      duration_ms BIGINT NOT NULL DEFAULT 0,
                      offset_ms BIGINT NOT NULL DEFAULT 0,
                      source_hash CHAR(64) NOT NULL,
                      language VARCHAR(16) NOT NULL DEFAULT 'zh',
                      index_version INT NOT NULL DEFAULT 1,
                      created_at BIGINT NOT NULL,
                      updated_at BIGINT NOT NULL,
                      UNIQUE KEY uk_video (platform, platform_video_id, part_index),
                      KEY idx_video_course (course_id)
                    ) DEFAULT CHARSET=utf8mb4
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cues (
                      id BIGINT AUTO_INCREMENT PRIMARY KEY,
                      video_id VARCHAR(64) NOT NULL,
                      seq INT NOT NULL,
                      start_ms BIGINT NOT NULL,
                      end_ms BIGINT NOT NULL,
                      text TEXT NOT NULL,
                      UNIQUE KEY uk_cue (video_id, seq),
                      KEY idx_cue_time (video_id, start_ms)
                    ) DEFAULT CHARSET=utf8mb4
                    """
                )
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS passages (
                      id VARCHAR(80) PRIMARY KEY,
                      video_id VARCHAR(64) NOT NULL,
                      course_id VARCHAR(48) NOT NULL,
                      start_ms BIGINT NOT NULL,
                      end_ms BIGINT NOT NULL,
                      text TEXT NOT NULL,
                      tokens TEXT NOT NULL,
                      cue_start_seq INT NOT NULL,
                      cue_end_seq INT NOT NULL,
                      embedding VECTOR({DIMENSION}) NULL,
                      index_version INT NOT NULL DEFAULT 1,
                      FULLTEXT KEY ft_passages (text) WITH PARSER ik,
                      VECTOR KEY vec_passages (embedding)
                        WITH (DISTANCE=COSINE, TYPE=HNSW, LIB=VSAG),
                      KEY idx_passage_video (video_id, start_ms),
                      KEY idx_passage_course (course_id)
                    ) DEFAULT CHARSET=utf8mb4
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS playlists (
                      id VARCHAR(64) PRIMARY KEY,
                      title VARCHAR(200) NOT NULL,
                      topic VARCHAR(300) NOT NULL,
                      budget_ms BIGINT NOT NULL,
                      created_at BIGINT NOT NULL
                    ) DEFAULT CHARSET=utf8mb4
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS playlist_items (
                      id BIGINT AUTO_INCREMENT PRIMARY KEY,
                      playlist_id VARCHAR(64) NOT NULL,
                      passage_id VARCHAR(80) NOT NULL,
                      rank INT NOT NULL,
                      clip_start_ms BIGINT NOT NULL,
                      clip_end_ms BIGINT NOT NULL,
                      reason VARCHAR(500) NOT NULL DEFAULT '',
                      KEY idx_item_playlist (playlist_id, rank)
                    ) DEFAULT CHARSET=utf8mb4
                    """
                )
                for key, value in {
                    "schema_version": SCHEMA_VERSION,
                    "embedding_model": MODEL_LABEL,
                    "embedding_dim": str(DIMENSION),
                    "chunk_version": CHUNK_VERSION,
                    "index_version": "1",
                }.items():
                    cur.execute(
                        "INSERT INTO meta(k, v) VALUES(%s, %s) "
                        "ON DUPLICATE KEY UPDATE v=VALUES(v)",
                        (key, value),
                    )
        finally:
            conn.close()
        self._schema_ready = True

    # ---------- metadata ----------
    def meta(self) -> dict[str, str]:
        self.ensure_schema()
        with self.cursor() as cur:
            cur.execute("SELECT k, v FROM meta")
            return {row["k"]: row["v"] for row in cur.fetchall()}

    def set_meta(self, key: str, value: str) -> None:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO meta(k, v) VALUES(%s, %s) ON DUPLICATE KEY UPDATE v=VALUES(v)",
                (key, value),
            )

    def counts(self) -> dict[str, int]:
        self.ensure_schema()
        with self.cursor() as cur:
            out: dict[str, int] = {}
            for table in ("videos", "cues", "passages", "playlists"):
                cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
                out[table] = int(cur.fetchone()["n"])
            cur.execute(
                "SELECT COUNT(*) AS n FROM courses c "
                "WHERE EXISTS (SELECT 1 FROM videos v WHERE v.course_id = c.id)"
            )
            out["courses"] = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(*) AS n FROM passages WHERE embedding IS NOT NULL")
            out["embedded_passages"] = int(cur.fetchone()["n"])
            return out

    def upsert_course(self, course_id: str, name: str, term: str = "") -> None:
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO courses(id, name, term, created_at) VALUES(%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name=VALUES(name), term=VALUES(term)
                """,
                (course_id, name, term, int(time.time())),
            )

    def list_courses(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.name, c.term,
                       COUNT(DISTINCT v.id) AS video_count,
                       COALESCE(SUM((SELECT COUNT(*) FROM cues q WHERE q.video_id = v.id)), 0) AS cue_count,
                       COALESCE(SUM((SELECT COUNT(*) FROM passages p WHERE p.video_id = v.id)), 0) AS passage_count
                FROM courses c LEFT JOIN videos v ON v.course_id = c.id
                GROUP BY c.id, c.name, c.term
                HAVING COUNT(DISTINCT v.id) > 0
                ORDER BY c.created_at, c.id
                """
            )
            rows = list(cur.fetchall())
            for row in rows:
                for key in ("video_count", "cue_count", "passage_count"):
                    if row.get(key) is not None:
                        row[key] = int(row[key])
            return rows

    def list_videos(self, course_id: str | None = None) -> list[dict[str, Any]]:
        self.ensure_schema()
        sql = """
            SELECT v.id, v.course_id, v.title, v.source_url, v.source_type, v.platform,
                   v.platform_video_id, v.part_index, v.cid, v.subtitle_kind,
                   v.duration_ms, v.offset_ms, v.source_hash, v.language, v.index_version,
                   (SELECT COUNT(*) FROM cues q WHERE q.video_id = v.id) AS cue_count,
                   (SELECT COUNT(*) FROM passages p WHERE p.video_id = v.id) AS passage_count,
                   (SELECT COUNT(*) FROM passages p WHERE p.video_id = v.id AND p.embedding IS NOT NULL) AS embedded_count
            FROM videos v
        """
        params: tuple[Any, ...] = ()
        if course_id:
            sql += " WHERE v.course_id = %s"
            params = (course_id,)
        sql += " ORDER BY v.course_id, v.part_index, v.id"
        with self.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def get_video_cues(self, video_id: str) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self.cursor() as cur:
            cur.execute(
                "SELECT seq, start_ms, end_ms, text FROM cues WHERE video_id=%s ORDER BY seq",
                (video_id,),
            )
            return list(cur.fetchall())

    def get_passage(self, passage_id: str) -> dict[str, Any] | None:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM passages WHERE id=%s", (passage_id,))
            return cur.fetchone()

    # ---------- ingest ----------
    def ingest(
        self,
        *,
        course_id: str,
        course_name: str,
        term: str,
        video_id: str,
        title: str,
        source_url: str,
        source_type: str,
        platform: str,
        platform_video_id: str,
        part_index: int,
        cid: int | None,
        subtitle_kind: str,
        duration_ms: int,
        offset_ms: int,
        language: str,
        cues: list[RawCue],
        passage_drafts: list[Any],
        source_hash: str,
        embeddings: list[list[float]] | None,
        warnings: list[str],
        force: bool = False,
    ) -> IngestResult:
        self.ensure_schema()
        meta = self.meta()
        index_version = int(meta.get("index_version", "1"))
        conn = self._connect()
        try:
            conn.autocommit(False)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, source_hash, index_version FROM videos WHERE platform=%s "
                    "AND platform_video_id=%s AND part_index=%s FOR UPDATE",
                    (platform, platform_video_id, part_index),
                )
                existing = cur.fetchone()
                primary_video_id = existing["id"] if existing else video_id
                cur.execute("SELECT COUNT(*) AS n FROM cues WHERE video_id=%s", (primary_video_id,))
                existing_cues = int(cur.fetchone()["n"])
                unchanged = (
                    existing is not None
                    and not force
                    and existing["source_hash"] == source_hash
                    and int(existing["index_version"]) == index_version
                    and existing_cues == len(cues)
                )
                if unchanged:
                    cur.execute(
                        "SELECT COUNT(*) AS n FROM passages WHERE video_id=%s",
                        (primary_video_id,),
                    )
                    passages = int(cur.fetchone()["n"])
                    cur.execute(
                        "SELECT COUNT(*) AS n FROM passages WHERE video_id=%s AND embedding IS NOT NULL",
                        (primary_video_id,),
                    )
                    embedded = int(cur.fetchone()["n"])
                    conn.commit()
                    return IngestResult(
                        primary_video_id, "unchanged", existing_cues, passages, source_hash, embedded, warnings
                    )

                cur.execute(
                    """
                    INSERT INTO courses(id, name, term, created_at) VALUES(%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name=VALUES(name), term=VALUES(term)
                    """,
                    (course_id, course_name, term, int(time.time())),
                )
                now = int(time.time())
                cur.execute(
                    """
                    INSERT INTO videos(id, course_id, title, source_url, source_type, platform,
                      platform_video_id, part_index, cid, subtitle_kind, duration_ms, offset_ms,
                      source_hash, language, index_version, created_at, updated_at)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE course_id=VALUES(course_id), title=VALUES(title),
                      source_url=VALUES(source_url), source_type=VALUES(source_type),
                      cid=VALUES(cid), subtitle_kind=VALUES(subtitle_kind),
                      duration_ms=VALUES(duration_ms), offset_ms=VALUES(offset_ms),
                      source_hash=VALUES(source_hash), language=VALUES(language),
                      index_version=VALUES(index_version), updated_at=VALUES(updated_at)
                    """,
                    (
                        primary_video_id, course_id, title, source_url, source_type, platform,
                        platform_video_id, part_index, cid, subtitle_kind, duration_ms, offset_ms,
                        source_hash, language, index_version, now, now,
                    ),
                )
                cur.execute("DELETE FROM passages WHERE video_id=%s", (primary_video_id,))
                cur.execute("DELETE FROM cues WHERE video_id=%s", (primary_video_id,))
                cue_rows = [
                    (primary_video_id, c.seq, c.start_ms, c.end_ms, c.text) for c in cues
                ]
                cur.executemany(
                    "INSERT INTO cues(video_id, seq, start_ms, end_ms, text) VALUES(%s,%s,%s,%s,%s)",
                    cue_rows,
                )
                used_embeddings = 0
                for idx, draft in enumerate(passage_drafts):
                    passage_id = f"p-{primary_video_id}-{draft.cue_start_seq:04d}"
                    vec = None
                    if embeddings and idx < len(embeddings) and embeddings[idx]:
                        vec = _vector_literal(embeddings[idx])
                        used_embeddings += 1
                    if vec:
                        cur.execute(
                            """
                            INSERT INTO passages(id, video_id, course_id, start_ms, end_ms, text,
                              tokens, cue_start_seq, cue_end_seq, embedding, index_version)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            """,
                            (
                                passage_id, primary_video_id, course_id, draft.start_ms,
                                draft.end_ms, draft.text, "", draft.cue_start_seq,
                                draft.cue_end_seq, vec, index_version,
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO passages(id, video_id, course_id, start_ms, end_ms, text,
                              tokens, cue_start_seq, cue_end_seq, embedding, index_version)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s)
                            """,
                            (
                                passage_id, primary_video_id, course_id, draft.start_ms,
                                draft.end_ms, draft.text, "", draft.cue_start_seq,
                                draft.cue_end_seq, index_version,
                            ),
                        )
            conn.commit()
            return IngestResult(
                primary_video_id,
                "replaced" if existing else "created",
                len(cues),
                len(passage_drafts),
                source_hash,
                used_embeddings,
                warnings,
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def rebuild_passages(
        self,
        *,
        video_id: str,
        drafts: list[Any],
        embeddings: list[list[float]] | None,
    ) -> int:
        self.ensure_schema()
        meta = self.meta()
        index_version = int(meta.get("index_version", "1"))
        with self.cursor() as cur:
            cur.execute("SELECT course_id FROM videos WHERE id=%s", (video_id,))
            row = cur.fetchone()
            if not row:
                raise DatabaseUnavailable("视频不存在")
            cur.execute("DELETE FROM passages WHERE video_id=%s", (video_id,))
            for idx, draft in enumerate(drafts):
                vec = None
                if embeddings and idx < len(embeddings):
                    vec = _vector_literal(embeddings[idx])
                if vec:
                    cur.execute(
                        """INSERT INTO passages(id, video_id, course_id, start_ms, end_ms, text,
                        tokens, cue_start_seq, cue_end_seq, embedding, index_version)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            f"p-{video_id}-{draft.cue_start_seq:04d}", video_id, row["course_id"],
                            draft.start_ms, draft.end_ms, draft.text, "", draft.cue_start_seq,
                            draft.cue_end_seq, vec, index_version,
                        ),
                    )
                else:
                    cur.execute(
                        """INSERT INTO passages(id, video_id, course_id, start_ms, end_ms, text,
                        tokens, cue_start_seq, cue_end_seq, embedding, index_version)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s)""",
                        (
                            f"p-{video_id}-{draft.cue_start_seq:04d}", video_id, row["course_id"],
                            draft.start_ms, draft.end_ms, draft.text, "", draft.cue_start_seq,
                            draft.cue_end_seq, index_version,
                        ),
                    )
            cur.execute(
                "UPDATE videos SET index_version=%s, updated_at=%s WHERE id=%s",
                (index_version, int(time.time()), video_id),
            )
            return len(drafts)

    # ---------- search primitives ----------
    def search_lexical(
        self, query: str, limit: int, course_id: str | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT p.id AS passage_id, p.video_id, p.course_id, v.title AS video_title,
                   c.name AS course_name, p.start_ms, p.end_ms, p.cue_start_seq, p.cue_end_seq,
                   p.text, v.source_url, v.platform, v.platform_video_id, v.part_index,
                   v.offset_ms, MATCH(p.text) AGAINST(%s) AS lexical_score
            FROM passages p
            JOIN videos v ON v.id = p.video_id
            JOIN courses c ON c.id = p.course_id
            WHERE MATCH(p.text) AGAINST(%s)
        """
        params: list[Any] = [query, query]
        if course_id:
            sql += " AND p.course_id = %s"
            params.append(course_id)
        sql += " ORDER BY lexical_score DESC LIMIT %s"
        params.append(limit)
        with self.cursor() as cur:
            cur.execute(sql, tuple(params))
            return list(cur.fetchall())

    def search_semantic(
        self, vector: list[float], limit: int, course_id: str | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT p.id AS passage_id, p.video_id, p.course_id, v.title AS video_title,
                   c.name AS course_name, p.start_ms, p.end_ms, p.cue_start_seq, p.cue_end_seq,
                   p.text, v.source_url, v.platform, v.platform_video_id, v.part_index,
                   v.offset_ms, cosine_distance(p.embedding, %s) AS distance
            FROM passages p
            JOIN videos v ON v.id = p.video_id
            JOIN courses c ON c.id = p.course_id
            WHERE p.embedding IS NOT NULL
        """
        params: list[Any] = [_vector_literal(vector)]
        if course_id:
            sql += " AND p.course_id = %s"
            params.append(course_id)
        sql += " ORDER BY distance ASC LIMIT %s"
        params.append(limit)
        with self.cursor() as cur:
            cur.execute(sql, tuple(params))
            return list(cur.fetchall())

    def cues_for_range(
        self, video_id: str, start_seq: int, end_seq: int
    ) -> list[dict[str, Any]]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT seq, start_ms, end_ms, text FROM cues WHERE video_id=%s "
                "AND seq BETWEEN %s AND %s ORDER BY seq",
                (video_id, start_seq, end_seq),
            )
            return list(cur.fetchall())

    # ---------- playlists (P2) ----------
    def save_playlist(
        self, playlist_id: str, title: str, topic: str, budget_ms: int, items: list[dict[str, Any]]
    ) -> None:
        self.ensure_schema()
        conn = self._connect()
        try:
            conn.autocommit(False)
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO playlists(id, title, topic, budget_ms, created_at) VALUES(%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE title=VALUES(title), topic=VALUES(topic), "
                    "budget_ms=VALUES(budget_ms)",
                    (playlist_id, title, topic, budget_ms, int(time.time())),
                )
                cur.execute("DELETE FROM playlist_items WHERE playlist_id=%s", (playlist_id,))
                cur.executemany(
                    "INSERT INTO playlist_items(playlist_id, passage_id, rank, clip_start_ms, "
                    "clip_end_ms, reason) VALUES(%s,%s,%s,%s,%s,%s)",
                    [
                        (
                            playlist_id, it["passage_id"], it["rank"], it["clip_start_ms"],
                            it["clip_end_ms"], it.get("reason", ""),
                        )
                        for it in items
                    ],
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_playlist(self, playlist_id: str) -> dict[str, Any] | None:
        self.ensure_schema()
        with self.cursor() as cur:
            cur.execute("SELECT * FROM playlists WHERE id=%s", (playlist_id,))
            playlist = cur.fetchone()
            if not playlist:
                return None
            cur.execute(
                """
                SELECT i.passage_id, i.rank, i.clip_start_ms, i.clip_end_ms, i.reason,
                       p.video_id, p.course_id, p.text, v.title AS video_title,
                       c.name AS course_name, v.source_url, v.platform, v.platform_video_id,
                       v.part_index, v.offset_ms
                FROM playlist_items i
                JOIN passages p ON p.id = i.passage_id
                JOIN videos v ON v.id = p.video_id
                JOIN courses c ON c.id = p.course_id
                WHERE i.playlist_id=%s ORDER BY i.rank
                """,
                (playlist_id,),
            )
            items = list(cur.fetchall())
            playlist["items"] = items
            return playlist

    def cues_raw(self, video_id: str) -> list[RawCue]:
        return [
            RawCue(seq=r["seq"], start_ms=r["start_ms"], end_ms=r["end_ms"], text=r["text"])
            for r in self.get_video_cues(video_id)
        ]

    def export_fixture(self, limit_videos: int = 10) -> dict[str, Any]:
        courses = self.list_courses()
        videos = self.list_videos()[:limit_videos]
        out_videos = []
        for v in videos:
            out_videos.append(
                {
                    "id": v["id"],
                    "course_id": v["course_id"],
                    "title": v["title"],
                    "source_url": v["source_url"],
                    "platform": v["platform"],
                    "platform_video_id": v["platform_video_id"],
                    "part_index": v["part_index"],
                    "duration_ms": v["duration_ms"],
                    "subtitle_kind": v["subtitle_kind"],
                    "cues": self.get_video_cues(v["id"]),
                    "passages": [
                        {
                            "id": p["id"],
                            "start_ms": p["start_ms"],
                            "end_ms": p["end_ms"],
                            "text": p["text"],
                            "cue_start_seq": p["cue_start_seq"],
                            "cue_end_seq": p["cue_end_seq"],
                        }
                        for p in self._passages_for_video(v["id"])
                    ],
                }
            )
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "exported from live seekdb",
            "mode": "demo",
            "courses": courses,
            "videos": out_videos,
        }

    def _passages_for_video(self, video_id: str) -> list[dict[str, Any]]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, start_ms, end_ms, text, cue_start_seq, cue_end_seq "
                "FROM passages WHERE video_id=%s ORDER BY start_ms",
                (video_id,),
            )
            return list(cur.fetchall())

    def dumps_for_debug(self) -> str:
        return json.dumps(self.counts(), ensure_ascii=False)
