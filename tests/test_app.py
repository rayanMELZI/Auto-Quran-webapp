import json

import pytest

from config import DEFAULT_SETTINGS
from factory import create_app
from routes import settings as settings_routes
from services import settings as settings_service


@pytest.fixture
def app(tmp_path):
    """Testing app: no scheduler; isolated settings path."""
    app = create_app("testing")
    app.config["SETTINGS_FILE"] = str(tmp_path / "settings.json")
    return app


def test_load_settings_merges_defaults(app, tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"default_keyword": "test keyword"}), encoding="utf-8")
    app.config["SETTINGS_FILE"] = str(settings_file)

    with app.app_context():
        settings = settings_service.load_settings()

    assert settings["default_keyword"] == "test keyword"
    assert settings["default_caption"] == DEFAULT_SETTINGS["default_caption"]
    assert settings["cronjob_enabled"] is False


def test_save_settings_writes_json(app, tmp_path):
    settings_file = tmp_path / "settings.json"
    app.config["SETTINGS_FILE"] = str(settings_file)

    payload = {
        "default_channel_url": "https://example.com/channel",
        "cronjob_enabled": True,
    }

    with app.app_context():
        assert settings_service.save_settings(payload) is True
    assert json.loads(settings_file.read_text(encoding="utf-8")) == payload


def test_api_settings_get_returns_saved_settings(app, tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"default_caption": "custom caption"}),
        encoding="utf-8",
    )
    app.config["SETTINGS_FILE"] = str(settings_file)

    client = app.test_client()
    response = client.get("/api/settings")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["settings"]["default_caption"] == "custom caption"


def test_api_settings_post_updates_file(app, tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps(DEFAULT_SETTINGS), encoding="utf-8")
    app.config["SETTINGS_FILE"] = str(settings_file)

    configure_calls = []
    monkeypatch.setattr(
        settings_routes,
        "configure_cronjob",
        lambda app_arg: configure_calls.append(True),
    )

    client = app.test_client()
    response = client.post("/api/settings", json={"default_keyword": "new keyword"})

    assert response.status_code == 200
    assert json.loads(settings_file.read_text(encoding="utf-8"))["default_keyword"] == "new keyword"
    assert configure_calls == []


def test_api_state_returns_pipeline_snapshot(app):
    client = app.test_client()
    response = client.get("/api/state")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "has_image": False,
        "has_video": False,
        "has_overlay": False,
        "has_final": False,
        "video_title": None,
    }
