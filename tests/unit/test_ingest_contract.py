from types import SimpleNamespace

import main
from domain import RawCue


def test_srt_ingest_forwards_cover_url(monkeypatch):
    captured = {}

    def fake_ingest(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            video_id=kwargs["video_id"],
            status="created",
            cue_count=2,
            passage_count=1,
            embedded_count=0,
            source_hash=kwargs["source_hash"],
            warnings=[],
        )

    monkeypatch.setattr(main.store, "ingest", fake_ingest)
    monkeypatch.setattr(main, "_embed", lambda texts, warnings: None)

    cues = [
        RawCue(seq=1, start_ms=0, end_ms=5000, text="第一句字幕"),
        RawCue(seq=2, start_ms=5000, end_ms=10000, text="第二句字幕"),
    ]
    main._ingest_cues(
        cues=cues,
        course_id="c-test",
        course_name="测试课程",
        term="2026 秋",
        title="测试讲次",
        source_url="",
        source_type="srt_upload",
        platform="local",
        platform_video_id="smoke",
        part_index=1,
        cid=None,
        cover_url="",
        subtitle_kind="uploaded_srt",
        duration_ms=10000,
        offset_ms=0,
        language="zh",
        warnings=[],
    )

    assert captured["cover_url"] == ""
    assert captured["platform_video_id"] == "smoke"
