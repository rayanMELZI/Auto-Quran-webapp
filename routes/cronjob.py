from flask import Blueprint, current_app, jsonify, request

from services.settings import load_settings, save_settings
from services.scheduler import configure_cronjob, get_scheduler

bp = Blueprint("cronjob", __name__)


@bp.route("/api/cronjob/status", methods=["GET"])
def api_cronjob_status():
    """Get cronjob status"""
    try:
        settings = load_settings()
        scheduler = get_scheduler(current_app._get_current_object())
        jobs = scheduler.get_jobs() if scheduler else []

        return jsonify(
            {
                "success": True,
                "enabled": settings.get("cronjob_enabled", False),
                "interval_hours": settings.get("cronjob_interval_hours", 24),
                "time": settings.get("cronjob_time", "09:00"),
                "active_jobs": len(jobs),
                "next_run": str(jobs[0].next_run_time) if jobs else None,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/cronjob/configure", methods=["POST"])
def api_cronjob_configure():
    """Configure and start/stop cronjob"""
    try:
        data = request.get_json() or {}
        settings = load_settings()

        if "enabled" in data:
            settings["cronjob_enabled"] = data["enabled"]
        if "interval_hours" in data:
            settings["cronjob_interval_hours"] = data["interval_hours"]
        if "time" in data:
            settings["cronjob_time"] = data["time"]

        save_settings(settings)
        configure_cronjob(current_app._get_current_object())

        return jsonify({"success": True, "message": "Cronjob configured successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
