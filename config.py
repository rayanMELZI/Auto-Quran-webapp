import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_SETTINGS = {
    "default_channel_url": "https://www.youtube.com/@Am9li9/videos",
    "default_keyword": "سورة",
    "default_caption": (
        "⚠️لا تنسوا اخواننا المستضعفين بالدعاء رحمكم الله⚠️\n\n"
        "#اكتب_شي_تؤجر_عليه #لاتنسى_ذكر_الله\n\n"
        "#الله #اكتب_شي_تؤجر_عليه #الله_أكبر #قران_كريم #لاتنسى_ذكر_الله #تلاوات #اللهم_امين"
    ),
    "default_image_path": None,
    "cronjob_enabled": False,
    "cronjob_interval_hours": 24,
    "cronjob_time": "09:00",
}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    BASE_DIR = BASE_DIR
    ASSETS_DIR = str(BASE_DIR / "assets")
    OUTPUT_DIR = str(BASE_DIR / "output")
    DATA_DIR = str(BASE_DIR / "data")
    SETTINGS_FILE = os.environ.get(
        "SETTINGS_FILE", str(BASE_DIR / "assets" / "settings.json")
    )
    DEFAULT_SETTINGS = DEFAULT_SETTINGS
    SCHEDULER_ENABLED = True
    GUNICORN_WORKERS = int(os.environ.get("GUNICORN_WORKERS", "1"))
    GUNICORN_THREADS = int(os.environ.get("GUNICORN_THREADS", "8"))


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SCHEDULER_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def select_config_class(config_name=None):
    if config_name and config_name in CONFIG_MAP:
        return CONFIG_MAP[config_name]
    explicit = os.environ.get("APP_CONFIG", "").strip().lower()
    if explicit in CONFIG_MAP:
        return CONFIG_MAP[explicit]
    if os.environ.get("FLASK_ENV", "").strip().lower() == "development":
        return DevelopmentConfig
    if os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes"):
        return DevelopmentConfig
    return ProductionConfig
