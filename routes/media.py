from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from services.pipeline_runtime import get_state
from services.settings import load_settings, save_settings

bp = Blueprint("media", __name__)


@bp.route("/api/preview/<media_type>")
def api_preview(media_type):
    """Serve media files for preview"""
    try:
        state = get_state(current_app._get_current_object())
        ps = state.pipeline_state
        if media_type == "image":
            path = ps.get("image_path", "assets/nature_image.jpg")
        elif media_type == "video":
            path = ps.get("video_path", "assets/quran_video.mp4")
        elif media_type == "overlay":
            path = ps.get("text_overlay_path", "assets/quran_text_frame.mov")
        elif media_type == "final":
            path = ps.get("final_video_path", "output/final_output.mp4")
        else:
            return jsonify({"error": "Invalid media type"}), 400

        if path and Path(path).exists():
            return send_file(path)
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/upload-image", methods=["POST"])
def api_upload_image():
    """Upload a custom image"""
    try:
        if "image" not in request.files:
            return jsonify({"success": False, "message": "No image file provided"}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No file selected"}), 400

        upload_path = "assets/custom_image.jpg"
        file.save(upload_path)

        save_as_default = request.form.get("save_as_default") == "true"
        if save_as_default:
            settings = load_settings()
            settings["default_image_path"] = upload_path
            save_settings(settings)

        state = get_state(current_app._get_current_object())
        state.pipeline_state["image_path"] = upload_path

        return jsonify(
            {
                "success": True,
                "message": "Image uploaded successfully",
                "path": upload_path,
                "preview_url": "/api/preview/custom",
                "saved_as_default": save_as_default,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/preview/custom")
def api_preview_custom():
    """Serve custom uploaded image"""
    try:
        path = "assets/custom_image.jpg"
        if Path(path).exists():
            return send_file(path)
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
