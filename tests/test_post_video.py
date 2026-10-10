import io
import os

import pytest

from config import DEFAULT_SETTINGS
from factory import create_app
from routes import instagram as instagram_routes


@pytest.fixture
def app(tmp_path):
    app = create_app("testing")
    app.config["SETTINGS_FILE"] = str(tmp_path / "settings.json")
    app.config["OUTPUT_DIR"] = str(tmp_path)
    return app


@pytest.fixture
def posted(monkeypatch):
    calls = []

    def fake_post(video_path, caption, thumbnail_path):
        calls.append({"video_path": video_path, "caption": caption, "thumbnail_path": thumbnail_path})
        return {"success": True, "message": "Posted successfully (media id 1)."}

    monkeypatch.setattr(instagram_routes, "post_to_instagram", fake_post)
    monkeypatch.setattr(instagram_routes, "_extract_cover", lambda video, thumb: thumb)
    return calls


def _upload(client, **form):
    data = {"video": (io.BytesIO(b"fake mp4 bytes"), "reel.mp4"), **form}
    return client.post("/api/post-video", data=data, content_type="multipart/form-data")


def test_health(app):
    assert app.test_client().get("/api/health").get_json() == {"status": "ok"}


def test_post_video_rejects_get(app):
    assert app.test_client().get("/api/post-video").status_code == 405


def test_post_video_requires_file(app, posted):
    response = app.test_client().post("/api/post-video")
    assert response.status_code == 400
    assert posted == []


def test_post_video_saves_upload_and_posts(app, posted, tmp_path):
    response = _upload(app.test_client(), caption="Al-Baqarah 1-7\nsecond line")

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    call = posted[0]
    assert call["caption"] == "Al-Baqarah 1-7\nsecond line"
    assert os.path.dirname(call["video_path"]) == str(tmp_path)
    with open(call["video_path"], "rb") as f:
        assert f.read() == b"fake mp4 bytes"
    assert call["thumbnail_path"].endswith(".jpg")


def test_post_video_uses_default_caption(app, posted):
    _upload(app.test_client())
    assert posted[0]["caption"] == DEFAULT_SETTINGS["default_caption"]


def test_post_video_reports_instagram_failure(app, monkeypatch):
    monkeypatch.setattr(instagram_routes, "_extract_cover", lambda video, thumb: "")
    monkeypatch.setattr(
        instagram_routes,
        "post_to_instagram",
        lambda **kw: {"success": False, "message": "rate limited", "error_category": "rate_limit"},
    )
    response = _upload(app.test_client())

    assert response.status_code == 503
    assert response.get_json()["error_category"] == "rate_limit"
