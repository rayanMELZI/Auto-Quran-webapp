import json
from copy import deepcopy
from pathlib import Path

from flask import current_app


def load_settings():
    """Load settings from JSON file (merged with defaults from config)."""
    settings_file = current_app.config["SETTINGS_FILE"]
    defaults = deepcopy(current_app.config["DEFAULT_SETTINGS"])
    if not Path(settings_file).exists():
        return defaults
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
            merged = deepcopy(defaults)
            if isinstance(saved, dict):
                merged.update(saved)
            return merged
    except Exception:
        return defaults


def save_settings(settings) -> bool:
    """Persist settings dict to JSON file."""
    settings_file = current_app.config["SETTINGS_FILE"]
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False
