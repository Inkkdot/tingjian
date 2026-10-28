import hashlib

import pytest

import bilibili
from bilibili import BilibiliClient, validate_track
from config import Settings
from domain import ImportFailed, RawCue


def cue(seq: int, start_ms: int, end_ms: int, text: str = "句子") -> RawCue:
    return RawCue(seq=seq, start_ms=start_ms, end_ms=end_ms, text=text)


def test_wbi_query_is_signed_and_sorted(monkeypatch):
    client = BilibiliClient(cookie="SESSDATA=test")
    key = "0123456789abcdef0123456789abcdef"
    monkeypatch.setattr(client, "_ensure_wbi_key", lambda: key)
    monkeypatch.setattr(bilibili.time, "time", lambda: 1700000000)

    query = client._wbi_query({"cid": 123, "bvid": "BV1xx411c7mD"})
    base = "bvid=BV1xx411c7mD&cid=123&wts=1700000000"
    expected = base + "&w_rid=" + hashlib.md5((base + key).encode()).hexdigest()
    assert query == expected


def test_wbi_query_empty_without_key(monkeypatch):
    client = BilibiliClient()
    monkeypatch.setattr(client, "_ensure_wbi_key", lambda: "")
    assert client._wbi_query({"bvid": "BV1xx411c7mD", "cid": 1}) == ""


def test_fetch_subtitles_prefers_signed_endpoint(monkeypatch):
    client = BilibiliClient(cookie="SESSDATA=test")
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(client, "_wbi_query", lambda params: "bvid=BV1&cid=1&wts=1&w_rid=x")

    def fake_get(path, params=None, query=""):
        calls.append((path, query))
        return {
            "data": {
                "subtitle": {
                    "subtitles": [
                        {
                            "lan": "ai-zh",
                            "lan_doc": "中文",
                            "subtitle_url": "//aisubtitle.example/x",
                            "ai_status": 2,
                        }
                    ]
                }
            }
        }

    monkeypatch.setattr(client, "_get_json", fake_get)
    tracks = client.fetch_subtitles("BV1xx411c7mD", 1)

    assert calls == [("/x/player/wbi/v2", "bvid=BV1&cid=1&wts=1&w_rid=x")]
    assert tracks[0].lan == "ai-zh"
    assert tracks[0].is_ai is True


def test_fetch_subtitles_falls_back_to_unsigned(monkeypatch):
    client = BilibiliClient()
    calls: list[str] = []
    monkeypatch.setattr(client, "_wbi_query", lambda params: "")

    def fake_get(path, params=None, query=""):
        calls.append(path)
        return {"data": {"subtitle": {"subtitles": []}}}

    monkeypatch.setattr(client, "_get_json", fake_get)
    assert client.fetch_subtitles("BV1xx411c7mD", 1) == []
    assert calls == ["/x/player/v2"]


def test_validate_track_accepts_full_coverage():
    cues = [cue(1, 6_000, 10_000), cue(2, 10_000, 2_318_000)]
    report = validate_track(cues, 2_318_000)
    assert report["cue_count"] == 2
    assert report["coverage"] == 1.0


def test_validate_track_rejects_truncated_track():
    cues = [cue(1, 0, 30_000), cue(2, 30_000, 63_000)]
    with pytest.raises(ImportFailed) as exc:
        validate_track(cues, 2_318_000)
    assert exc.value.code == "TRACK_MISMATCH"
    assert exc.value.detail["coverage"] < 0.1


def test_validate_track_rejects_overrun_track():
    cues = [cue(1, 0, 500_000), cue(2, 500_000, 2_600_000)]
    with pytest.raises(ImportFailed) as exc:
        validate_track(cues, 2_318_000)
    assert exc.value.code == "TRACK_MISMATCH"


def test_validate_track_skips_duration_check_when_unknown():
    report = validate_track([cue(1, 0, 5_000)], 0)
    assert report["coverage"] is None


def test_validate_track_rejects_empty():
    with pytest.raises(ImportFailed) as exc:
        validate_track([], 1_000)
    assert exc.value.code == "TRACK_NOT_AVAILABLE"


def test_settings_repr_hides_cookie():
    settings = Settings(bilibili_cookie="SESSDATA=secret-value")
    assert "secret-value" not in repr(settings)
    assert settings.bilibili_login_configured is True
