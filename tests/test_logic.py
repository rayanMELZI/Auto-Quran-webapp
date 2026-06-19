"""Unit tests for the pure pipeline logic (no network, no rendering)."""
from logic.scripts.download_quran_video import (
    _append_downloaded_id,
    _get_duration_seconds,
    _is_short,
    _load_downloaded_ids,
    _normalize_video_url,
)
from logic.scripts.main import DEFAULT_CAPTION, build_caption


class TestDuration:
    def test_get_duration_seconds_numeric(self):
        assert _get_duration_seconds({"duration": 42}) == 42.0
        assert _get_duration_seconds({"duration": "30"}) == 30.0

    def test_get_duration_seconds_missing_or_invalid(self):
        assert _get_duration_seconds({}) is None
        assert _get_duration_seconds({"duration": None}) is None
        assert _get_duration_seconds({"duration": "abc"}) is None
        assert _get_duration_seconds({"duration": 0}) is None

    def test_is_short_within_limit(self):
        assert _is_short({"duration": 45}, 60) is True
        assert _is_short({"duration": 60}, 60) is True

    def test_is_short_too_long(self):
        assert _is_short({"duration": 61}, 60) is False
        assert _is_short({"duration": 600}, 60) is False

    def test_is_short_unknown_duration_is_not_short(self):
        # Unknown length must never be treated as short (we don't risk a long download)
        assert _is_short({}, 60) is False
        assert _is_short({"duration": None}, 60) is False


class TestNormalizeUrl:
    def test_prefers_webpage_url(self):
        assert _normalize_video_url({"webpage_url": "https://youtu.be/x"}) == "https://youtu.be/x"

    def test_builds_url_from_id(self):
        assert _normalize_video_url({"id": "abc123"}) == "https://www.youtube.com/watch?v=abc123"


class TestDownloadedIds:
    def test_roundtrip(self, tmp_path):
        f = tmp_path / "downloaded.txt"
        assert _load_downloaded_ids(f) == set()
        _append_downloaded_id(f, "id1")
        _append_downloaded_id(f, "id2")
        assert _load_downloaded_ids(f) == {"id1", "id2"}


class TestCaption:
    def test_custom_caption_wins(self):
        assert build_caption(video_title="t", custom_caption="hello") == "hello"

    def test_title_caption(self):
        out = build_caption(video_title="Surah Maryam")
        assert out.startswith("Surah Maryam")
        assert "#Quran" in out

    def test_default_caption_fallback(self):
        assert build_caption() == DEFAULT_CAPTION
