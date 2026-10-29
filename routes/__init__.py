from flask import Flask


def register_blueprints(app: Flask) -> None:
    from routes.cronjob import bp as cronjob_bp
    from routes.instagram import bp as instagram_bp
    from routes.main import bp as main_bp
    from routes.media import bp as media_bp
    from routes.pipeline import bp as pipeline_bp
    from routes.settings import bp as settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(instagram_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(cronjob_bp)
