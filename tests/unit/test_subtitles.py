import pytest

from domain import BadSubtitle, RawCue
from subtitles import chunk_passages, coverage_report, parse_subtitle, source_hash


def test_parse_srt_bom_crlf_and_multiline():
    content = (
        "\ufeff1\r\n00:00:00,500 --> 00:00:02,000\r\n第一行\r\n第二行\r\n\r\n"
        "2\r\n00:00:02,100 --> 00:00:04,000\r\n<i>下一句</i>\r\n"
    )
    parsed = parse_subtitle(content, "demo.srt")
    assert len(parsed.cues) == 2
    assert parsed.cues[0].text == "第一行 第二行"
    assert parsed.cues[0].start_ms == 500
    assert parsed.cues[1].text == "下一句"
    assert parsed.cues[1].end_ms == 4000


def test_parse_vtt():
    content = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n你好\n\n00:00:04.000 --> 00:00:06.000\n世界\n"
    parsed = parse_subtitle(content, "demo.vtt")
    assert [cue.text for cue in parsed.cues] == ["你好", "世界"]


def test_reject_inverted_time_range():
    content = "1\n00:00:05,000 --> 00:00:02,000\n非法\n"
    with pytest.raises(BadSubtitle):
        parse_subtitle(content, "bad.srt")


def test_chunking_covers_every_cue_with_one_overlap():
    cues = [
        RawCue(seq=i, start_ms=(i - 1) * 2000, end_ms=i * 2000, text=f"第{i}句字幕内容")
        for i in range(1, 31)
    ]
    drafts = chunk_passages(cues)
    report = coverage_report(cues, drafts)
    assert report["missing_cues"] == []
    assert report["covered_cues"] == 30
    for draft in drafts:
        assert draft.end_ms > draft.start_ms
        assert draft.end_ms - draft.start_ms <= 45_000
        assert draft.cue_start_seq <= draft.cue_end_seq
    for previous, current in zip(drafts, drafts[1:]):
        assert current.cue_start_seq <= previous.cue_end_seq + 1


def test_chunking_keeps_long_single_cue():
    cues = [RawCue(seq=1, start_ms=0, end_ms=90_000, text="超长单条字幕" * 50)]
    drafts = chunk_passages(cues)
    assert len(drafts) == 1
    assert coverage_report(cues, drafts)["missing_cues"] == []


def test_source_hash_stable_and_content_sensitive():
    cues = [RawCue(seq=1, start_ms=0, end_ms=1000, text="原文")]
    kwargs = dict(
        platform="local",
        platform_video_id="v1",
        part_index=1,
        language="zh",
        source_type="srt_upload",
    )
    first = source_hash(cues=cues, **kwargs)
    second = source_hash(cues=[RawCue(seq=1, start_ms=0, end_ms=1000, text=" 原文 ")], **kwargs)
    changed = source_hash(cues=[RawCue(seq=1, start_ms=0, end_ms=1000, text="改过")], **kwargs)
    assert first == second
    assert first != changed
    assert len(first) == 64
