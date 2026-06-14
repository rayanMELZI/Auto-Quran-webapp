from copy import deepcopy

from flask import Blueprint, current_app, jsonify, request

from services.settings import load_settings, save_settings
from services.scheduler import configure_cronjob

bp = Blueprint("settings", __name__)


@bp.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    """Get or update user settings"""
    if request.method == "GET":
        settings = load_settings()
        return jsonify({"success": True, "settings": settings})
    try:
        data = request.get_json() or {}
        settings = load_settings()
        settings.update(data)

        if save_settings(settings):
            if (
                "cronjob_enabled" in data
                or "cronjob_interval_hours" in data
                or "cronjob_time" in data
            ):
                # configure_cronjob(current_app._get_current_object())  
                configure_cronjob(getattr(current_app, "_get_current_object")())  

            return jsonify({"success": True, "message": "Settings saved successfully"})
        return jsonify({"success": False, "message": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/settings/reset-default", methods=["POST"])
def api_settings_reset_default():
    """Reset one setting key to its predefined default value"""
    try:
        data = request.get_json() or {}
        key = data.get("key")
        defaults = current_app.config["DEFAULT_SETTINGS"]
        if key not in defaults:
            return jsonify({"success": False, "message": "Invalid settings key"}), 400

        settings = load_settings()
        settings[key] = deepcopy(defaults[key])

        if not save_settings(settings):
            return jsonify({"success": False, "message": "Failed to save settings"}), 500

        if key in ("cronjob_enabled", "cronjob_interval_hours", "cronjob_time"):
            # configure_cronjob(current_app._get_current_object())
            configure_cronjob(getattr(current_app, "_get_current_object")())

        return jsonify(
            {
                "success": True,
                "message": f"{key} reset to default",
                "key": key,
                "value": settings.get(key),
                "settings": settings,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
