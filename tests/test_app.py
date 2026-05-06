import json

import app as app_module


def test_load_settings_merges_defaults(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"default_keyword": "test keyword"}), encoding="utf-8")
    monkeypatch.setattr(app_module, "SETTINGS_FILE", str(settings_file))

    settings = app_module.load_settings()

    assert settings["default_keyword"] == "test keyword"
    assert settings["default_caption"] == app_module.DEFAULT_SETTINGS["default_caption"]
    assert settings["cronjob_enabled"] is False


def test_save_settings_writes_json(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(app_module, "SETTINGS_FILE", str(settings_file))

    payload = {
        "default_channel_url": "https://example.com/channel",
        "cronjob_enabled": True,
    }

    assert app_module.save_settings(payload) is True
    assert json.loads(settings_file.read_text(encoding="utf-8")) == payload


def test_api_settings_get_returns_saved_settings(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"default_caption": "custom caption"}), encoding="utf-8")
    monkeypatch.setattr(app_module, "SETTINGS_FILE", str(settings_file))

    client = app_module.app.test_client()
    response = client.get("/api/settings")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["settings"]["default_caption"] == "custom caption"


def test_api_settings_post_updates_file(tmp_path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps(app_module.DEFAULT_SETTINGS), encoding="utf-8")
    monkeypatch.setattr(app_module, "SETTINGS_FILE", str(settings_file))

    configure_calls = []
    monkeypatch.setattr(app_module, "configure_cronjob", lambda: configure_calls.append(True))

    client = app_module.app.test_client()
    response = client.post("/api/settings", json={"default_keyword": "new keyword"})

    assert response.status_code == 200
    assert json.loads(settings_file.read_text(encoding="utf-8"))["default_keyword"] == "new keyword"
    assert configure_calls == []


def test_api_state_returns_pipeline_snapshot():
    client = app_module.app.test_client()
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