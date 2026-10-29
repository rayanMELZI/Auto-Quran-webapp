import logging
import os

from dotenv import load_dotenv
from flask import Flask

from config import BASE_DIR, select_config_class
from services.pipeline_runtime import STATE_KEY, AppState

# Load .env once at import so INSTA_* and proxies are visible to Gunicorn/workers
load_dotenv(BASE_DIR / ".env", override=False)

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def create_app(config_name=None) -> Flask:
    """Application factory. Pass config_name='testing' for tests (no scheduler)."""
    app = Flask(__name__, template_folder="templates")

    config_cls = select_config_class(config_name)
    app.config.from_object(config_cls)

    os.makedirs(app.config["ASSETS_DIR"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_DIR"], exist_ok=True)
    os.makedirs(app.config["DATA_DIR"], exist_ok=True)

    app.extensions[STATE_KEY] = AppState()

    from routes import register_blueprints

    register_blueprints(app)

    with app.app_context():
        from services.scheduler import init_scheduler

        init_scheduler(app)

    return app
