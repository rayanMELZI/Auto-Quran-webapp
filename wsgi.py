"""WSGI entry for Gunicorn: ``gunicorn wsgi:app``."""

from factory import create_app

app = create_app()
