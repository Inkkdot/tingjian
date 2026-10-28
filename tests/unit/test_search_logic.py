from domain import SearchHit
from playback import clamp_start, jump_for
from search import dedupe_overlaps, filter_lexical, query_keywords


def test_query_keywords_drop_stopwords_and_keep_domain_terms():
    terms = query_keywords("为什么数据库要使用最左前缀原则？")
    assert "最左前缀" in terms
    assert "为什么" not in terms


def test_filter_lexical_requires_half_of_terms():
    rows = [
        {"text": "索引 范围 B+树", "id": 1},
        {"text": "索引 范围", "id": 2},
        {"text": "索引", "id": 3},
    ]
    kept = filter_lexical(rows, ["索引", "范围", "B+树"])
    assert [row["id"] for row in kept] == [1, 2]
    assert kept[0]["matched_terms"] == 3


def test_clamp_and_bilibili_jump():
    assert clamp_start(-500, 0) == 0
    url, capability = jump_for(
        platform="bilibili",
        source_url="",
        platform_video_id="BV1xx411c7mD",
        part_index=2,
        start_ms=754_000,
        offset_ms=1_000,
    )
    assert url == "https://www.bilibili.com/video/BV1xx411c7mD?p=2&t=755"
    assert capability == "external_seek"


def test_youtube_direct_and_local_capabilities():
    url, cap = jump_for(
        platform="youtube",
        source_url="",
        platform_video_id="abc123",
        part_index=1,
        start_ms=61_000,
    )
    assert url == "https://www.youtube.com/watch?v=abc123&t=61s"
    assert cap == "external_seek"

    url, cap = jump_for(
        platform="generic",
        source_url="https://cdn.example.com/lecture.mp4",
        platform_video_id="",
        part_index=1,
        start_ms=2_000,
    )
    assert url == "https://cdn.example.com/lecture.mp4?t=2.0"
    assert cap == "url_hint"

    assert jump_for(
        platform="local", source_url="", platform_video_id="", part_index=1, start_ms=1
    ) == ("", "local_select")


def _hit(passage_id: str, video_id: str, start: int, end: int, score: float) -> SearchHit:
    return SearchHit(
        passage_id=passage_id,
        video_id=video_id,
        course_id="c1",
        video_title="t",
        course_name="c",
        start_ms=start,
        end_ms=end,
        cue_start_seq=1,
        cue_end_seq=2,
        text="x",
        source_url="",
        jump_url="",
        playback_capability="local_select",
        match_reason="test",
        score=score,
    )


def test_dedupe_overlaps_same_video_only():
    hits = [
        _hit("p1", "v1", 0, 40_000, 0.9),
        _hit("p2", "v1", 5_000, 45_000, 0.8),
        _hit("p3", "v2", 0, 40_000, 0.7),
    ]
    kept = dedupe_overlaps(hits, threshold=0.6)
    assert [hit.passage_id for hit in kept] == ["p1", "p3"]


def test_union_length_merges_overlapping_ranges():
    from review import _union_length

    assert _union_length([(0, 1000), (2000, 3000)]) == 2000
    assert _union_length([(0, 1000), (500, 1500)]) == 1500
    assert _union_length([(0, 1000), (200, 300)]) == 1000
    assert _union_length([]) == 0
