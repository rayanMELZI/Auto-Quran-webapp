"""API tests using Flask's test client.

The heavy pipeline functions (downloads, ffmpeg, MoviePy, Instagram) are
monkeypatched so these tests run fast and offline.
"""
import json

import pytest


@pytest.fixture
def app_module(monkeypatch, tmp_path):
    import app as app_module

    # Isolate settings so tests never touch the real assets/settings.json
    monkeypatch.setattr(app_module, "SETTINGS_FILE", str(tmp_path / "settings.json"))

    # Start every test from a clean in-memory pipeline state
    app_module.pipeline_state.clear()
    app_module.pipeline_state.update(
        {
            "image_path": None,
            "video_path": None,
            "video_title": None,
            "text_overlay_path": None,
            "final_video_path": None,
        }
    )
    return app_module


@pytest.fixture
def client(app_module):
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def _json(resp):
    return json.loads(resp.data)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert _json(resp)["status"] == "healthy"


def test_state_defaults(client):
    body = _json(client.get("/api/state"))
    assert body["has_image"] is False
    assert body["has_video"] is False
    assert body["has_final"] is False


def test_settings_get_and_roundtrip(client):
    body = _json(client.get("/api/settings"))
    assert body["success"] is True
    assert "default_keyword" in body["settings"]

    client.post("/api/settings", json={"default_keyword": "KW123"})
    assert _json(client.get("/api/settings"))["settings"]["default_keyword"] == "KW123"

    client.post("/api/settings/reset-default", json={"key": "default_keyword"})
    assert _json(client.get("/api/settings"))["settings"]["default_keyword"] == "سورة"


def test_gates_return_400_when_nothing_ready(client):
    assert client.post("/api/extract-text", json={}).status_code == 400
    assert client.post("/api/create-final-video", json={}).status_code == 400
    assert client.post("/api/post-to-instagram", json={}).status_code == 400


def test_download_image_success(client, app_module, monkeypatch):
    monkeypatch.setattr(app_module, "download_nature_image", lambda *a, **k: "assets/nature_image.jpg")
    body = _json(client.post("/api/download-image", json={"query": "forest"}))
    assert body["success"] is True
    assert app_module.pipeline_state["image_path"] == "assets/nature_image.jpg"


def test_download_video_duplicate_returns_409(client, app_module, monkeypatch):
    def fake_dl(*a, **k):
        return None, None, {"duplicate": True, "message": "already downloaded"}

    monkeypatch.setattr(app_module, "download_quran_video", fake_dl)
    resp = client.post("/api/download-video", json={})
    assert resp.status_code == 409
    assert _json(resp)["duplicate"] is True


def test_download_video_too_long_returns_500(client, app_module, monkeypatch):
    def fake_dl(*a, **k):
        return None, None, {"duplicate": False, "message": "Video is too long (90s)."}

    monkeypatch.setattr(app_module, "download_quran_video", fake_dl)
    resp = client.post("/api/download-video", json={})
    assert resp.status_code == 500
    assert "too long" in _json(resp)["message"]
