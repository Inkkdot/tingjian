import pymysql
import pytest

from config import settings

pytestmark = pytest.mark.integration

SAMPLE = """1
00:00:00,000 --> 00:00:06,000
事务的原子性保证一组操作要么全部成功要么全部失败。

2
00:00:06,000 --> 00:00:12,000
如果中途失败，已经执行的操作必须全部撤销。

3
00:00:12,000 --> 00:00:18,000
隔离性描述并发事务之间如何互不干扰。

4
00:00:18,000 --> 00:00:24,000
持久性表示提交后的数据不会因为宕机而丢失。

5
00:00:24,000 --> 00:00:30,000
数据库通过日志保证原子性和持久性。

6
00:00:30,000 --> 00:00:36,000
隔离级别越高，并发度通常越低。
"""


@pytest.fixture(scope="function")
def test_store():
    assert settings.db_name.endswith("_test"), "integration tests must use a *_test database"
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        charset="utf8mb4",
        autocommit=True,
    )
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS `{settings.db_name}`")
        cur.execute(f"CREATE DATABASE `{settings.db_name}` CHARACTER SET utf8mb4")
    conn.close()
    from store import Store

    store = Store()
    store.ensure_schema()
    return store


def _ingest(store, *, video_seed="srt-e2e-01", embeddings=None):
    from subtitles import chunk_passages, parse_subtitle, source_hash

    parsed = parse_subtitle(SAMPLE, "sample.srt")
    drafts = chunk_passages(parsed.cues)
    digest = source_hash(
        platform="local",
        platform_video_id=video_seed,
        part_index=1,
        language="zh",
        source_type="srt_upload",
        cues=parsed.cues,
    )
    return store.ingest(
        course_id="c-test",
        course_name="测试课程",
        term="2026 秋",
        video_id=f"v-{video_seed}",
        title="测试讲次",
        source_url="",
        source_type="srt_upload",
        platform="local",
        platform_video_id=video_seed,
        part_index=1,
        cid=None,
        cover_url="",
        subtitle_kind="uploaded_srt",
        duration_ms=parsed.cues[-1].end_ms,
        offset_ms=0,
        language="zh",
        cues=parsed.cues,
        passage_drafts=drafts,
        source_hash=digest,
        embeddings=embeddings,
        warnings=[],
    ), parsed, drafts


def test_schema_ingest_idempotent_and_traceable(test_store):
    first, parsed, drafts = _ingest(test_store)
    assert first.status == "created"
    assert first.cue_count == len(parsed.cues)
    assert first.passage_count == len(drafts)

    second, _, _ = _ingest(test_store)
    assert second.status == "unchanged"
    assert second.cue_count == first.cue_count
    assert second.passage_count == first.passage_count

    counts = test_store.counts()
    assert counts["videos"] == 1
    assert counts["cues"] == len(parsed.cues)

    cues = test_store.get_video_cues(first.video_id)
    assert cues[0]["start_ms"] == 0
    assert "原子性" in cues[0]["text"]
    assert [cue["seq"] for cue in cues] == list(range(1, len(parsed.cues) + 1))


def test_real_embedding_vector_and_hybrid_search(test_store):
    from embeddings import Embedder
    from search import search

    embedder = Embedder()
    parsed = __import__("subtitles").parse_subtitle(SAMPLE, "sample.srt")
    drafts = __import__("subtitles").chunk_passages(parsed.cues)
    vectors = embedder.embed_passages([draft.text for draft in drafts])
    assert len(vectors) == len(drafts)
    assert len(vectors[0]) == 512

    result, _, _ = _ingest(test_store, video_seed="srt-e2e-02", embeddings=vectors)
    assert result.embedded_count == len(drafts)

    lexical = test_store.search_lexical("原子性", 5)
    assert lexical and lexical[0]["video_id"] == result.video_id

    query_vector = embedder.embed_query("事务失败后如何恢复")
    semantic = test_store.search_semantic(query_vector, 5)
    assert semantic and semantic[0]["video_id"] == result.video_id
    assert 0.0 <= semantic[0]["distance"] <= 2.0

    outcome = search(test_store, embedder, "原子性和持久性", limit=3, mode="hybrid")
    assert outcome.hits
    assert outcome.hits[0].video_id == result.video_id
    assert outcome.hits[0].cue_start_seq >= 1
    assert outcome.hits[0].jump_url == ""
    assert outcome.hits[0].playback_capability == "local_select"
