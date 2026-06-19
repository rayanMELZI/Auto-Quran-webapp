"""Shared pytest setup.

Makes ``app`` and the ``logic`` package importable whether the tests run
inside the backend container (code lives in /app) or from the repo root
(app.py is in ./backend, logic/ is at the root).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

for candidate in ("/app", ROOT, os.path.join(ROOT, "backend")):
    if candidate and os.path.isdir(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)
