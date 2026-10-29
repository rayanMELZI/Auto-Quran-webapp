import logic.scripts.download_image as download_image_module


def test_download_nature_image_uses_fallback_when_api_key_is_missing(tmp_path, monkeypatch):
    fallback = tmp_path / "fallback.jpg"
    fallback.write_bytes(b"fallback image")
    monkeypatch.setattr(download_image_module, "load_dotenv", lambda: None)
    monkeypatch.setattr(download_image_module.os, "getenv", lambda _name: None)

    result = download_image_module.download_nature_image(
        output_path=str(tmp_path / "output.jpg"),
        fallback_path=str(fallback),
    )

    assert result == str(fallback)


def test_download_nature_image_returns_none_without_api_key_or_fallback(tmp_path, monkeypatch):
    missing_fallback = tmp_path / "missing.jpg"
    monkeypatch.setattr(download_image_module, "load_dotenv", lambda: None)
    monkeypatch.setattr(download_image_module.os, "getenv", lambda _name: None)

    result = download_image_module.download_nature_image(
        output_path=str(tmp_path / "output.jpg"),
        fallback_path=str(missing_fallback),
    )

    assert result is None