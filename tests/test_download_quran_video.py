from pathlib import Path

from logic.scripts.download_quran_video import (
    _build_meta,
    _extract_channel_id,
    _is_auth_challenge_error,
    _is_retryable_video_error,
    _load_downloaded_ids,
)


def test_extract_channel_id_handles_channel_and_videos_urls():
    assert _extract_channel_id("https://www.youtube.com/@ExampleChannel") == "ExampleChannel"
    assert _extract_channel_id("https://www.youtube.com/@ExampleChannel/videos") == "ExampleChannel"


def test_load_downloaded_ids_creates_missing_file(tmp_path):
    downloaded_file = tmp_path / "downloaded_videos.txt"

    result = _load_downloaded_ids(downloaded_file)

    assert result == set()
    assert downloaded_file.exists()


def test_build_meta_marks_duplicates():
    meta = _build_meta(video_id="abc123", duplicate=True, message="already downloaded")

    assert meta == {
        "video_id": "abc123",
        "source_type": "channel",
        "duplicate": True,
        "message": "already downloaded",
    }


def test_error_helpers_identify_retryable_cases():
    auth_error = RuntimeError("Sign in to confirm you're not a bot")
    format_error = RuntimeError("Requested format is not available")

    assert _is_auth_challenge_error(auth_error) is True
    assert _is_retryable_video_error(format_error) is True