from pathlib import Path
from threading import Thread

from flask import Blueprint, current_app, jsonify, request

from logic.scripts.create_final_video import create_final_video
from logic.scripts.download_image import download_nature_image
from logic.scripts.download_quran_video import download_quran_video
from logic.scripts.extract_text_from_video import extract_text_from_video
from services.pipeline_runtime import (
    finalize_progress,
    get_state,
    progress_snapshot,
    reset_progress,
    run_full_pipeline_bg,
    set_step,
)

bp = Blueprint("pipeline", __name__)


@bp.route("/api/download-image", methods=["POST"])
def api_download_image():
    """Download a nature image from Unsplash"""
    try:
        data = request.get_json() or {}
        query = data.get("query", "nature landscape")

        image_path = download_nature_image(
            output_path="assets/nature_image.jpg",
            query=query,
        )

        state = get_state(current_app._get_current_object())
        if image_path:
            state.pipeline_state["image_path"] = image_path
            return jsonify(
                {
                    "success": True,
                    "message": "Image downloaded successfully",
                    "path": image_path,
                    "preview_url": "/api/preview/image",
                }
            )
        return jsonify({"success": False, "message": "Failed to download image"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/download-video", methods=["POST"])
def api_download_video():
    """Download a Quran video from YouTube"""
    try:
        data = request.get_json() or {}
        channel_url = data.get("channel_url", "https://www.youtube.com/@Am9li9/videos")
        keyword = data.get("keyword", "سورة")
        video_url = data.get("video_url")

        max_dur = data.get("max_video_duration_seconds")
        if max_dur is not None:
            try:
                max_dur = int(max_dur)
            except (TypeError, ValueError):
                max_dur = None

        video_path, video_title, meta = download_quran_video(
            channel_url=channel_url,
            output_path="assets/quran_video.mp4",
            title_keyword=keyword,
            video_url=video_url,
            max_duration_seconds=max_dur,
        )

        state = get_state(current_app._get_current_object())
        if video_path:
            state.pipeline_state["video_path"] = video_path
            state.pipeline_state["video_title"] = video_title
            return jsonify(
                {
                    "success": True,
                    "message": f"Video downloaded: {video_title}",
                    "path": video_path,
                    "title": video_title,
                    "preview_url": "/api/preview/video",
                }
            )
        message = meta.get("message") if isinstance(meta, dict) else None
        return (
            jsonify(
                {
                    "success": False,
                    "message": message or "Failed to download video",
                    "duplicate": bool(meta.get("duplicate")) if isinstance(meta, dict) else False,
                }
            ),
            409 if isinstance(meta, dict) and meta.get("duplicate") else 500,
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/extract-text", methods=["POST"])
def api_extract_text():
    """Extract transparent text overlay from video"""
    try:
        state = get_state(current_app._get_current_object())
        video_path = state.pipeline_state.get("video_path")

        if not video_path:
            return jsonify(
                {
                    "success": False,
                    "message": "No video available. Please download a video first.",
                }
            ), 400

        text_overlay_path = extract_text_from_video(
            video_path=video_path,
            output_path="assets/quran_text_frame.mov",
        )

        if text_overlay_path:
            state.pipeline_state["text_overlay_path"] = text_overlay_path
            return jsonify(
                {
                    "success": True,
                    "message": "Text overlay extracted successfully",
                    "path": text_overlay_path,
                    "preview_url": "/api/preview/overlay",
                }
            )
        return jsonify({"success": False, "message": "Failed to extract text overlay"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/create-final", methods=["POST"])
def api_create_final():
    """Create final video with image background and text overlay"""
    app = current_app._get_current_object()
    state = get_state(app)
    try:
        image_path = state.pipeline_state.get("image_path")
        video_path = state.pipeline_state.get("video_path")
        text_overlay_path = state.pipeline_state.get("text_overlay_path")

        if not image_path:
            return jsonify(
                {
                    "success": False,
                    "message": "No image available. Please download an image first.",
                }
            ), 400

        if not video_path:
            return jsonify(
                {
                    "success": False,
                    "message": "No video available. Please download a video first.",
                }
            ), 400

        reset_progress(app, "create-final", ["final"])
        set_step(app, "final", status="processing", progress=0, message="Creating final video...")

        final_video_path = create_final_video(
            image_path=image_path,
            quran_video_path=video_path,
            text_frame_path=text_overlay_path,
            output_path="output/final_output.mp4",
            progress_callback=lambda percent, msg: set_step(
                app, "final", status="processing", progress=percent, message=msg
            ),
        )

        if final_video_path:
            state.pipeline_state["final_video_path"] = final_video_path
            set_step(
                app,
                "final",
                status="completed",
                progress=100,
                message="Final video created successfully",
                result={
                    "path": final_video_path,
                    "preview_url": "/api/preview/final",
                },
            )
            finalize_progress(app, "Final video created successfully")
            return jsonify(
                {
                    "success": True,
                    "message": "Final video created successfully",
                    "path": final_video_path,
                    "preview_url": "/api/preview/final",
                }
            )
        set_step(app, "final", status="error", message="Failed to create final video")
        finalize_progress(app, "Failed to create final video")
        return jsonify({"success": False, "message": "Failed to create final video"}), 500
    except Exception as e:
        set_step(app, "final", status="error", message=f"Error: {str(e)}")
        finalize_progress(app, "Final video creation failed")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/run-full-pipeline", methods=["POST"])
def api_run_full_pipeline():
    """Run the complete pipeline from start to finish (non-blocking)"""
    try:
        data = request.get_json() or {}
        skip_text_overlay = data.get("skip_text_overlay", False)
        auto_post = data.get("auto_post", False)
        caption = data.get("caption", "")
        channel_url = data.get("channel_url", "https://www.youtube.com/@Am9li9/videos")
        keyword = data.get("keyword", "سورة")
        video_url = data.get("video_url")
        max_dur = data.get("max_video_duration_seconds")
        if max_dur is not None:
            try:
                max_dur = int(max_dur)
            except (TypeError, ValueError):
                max_dur = None

        app = current_app._get_current_object()
        state = get_state(app)
        state.stop_event.clear()

        bg_thread = Thread(
            target=run_full_pipeline_bg,
            args=(
                app,
                skip_text_overlay,
                auto_post,
                caption,
                channel_url,
                keyword,
                video_url,
                max_dur,
            ),
            daemon=True,
        )
        bg_thread.start()

        return jsonify(
            {
                "success": True,
                "message": "Pipeline started. Monitor progress via /api/progress endpoint.",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/progress")
def api_progress():
    """Get live progress for long-running operations"""
    return jsonify(progress_snapshot(current_app._get_current_object()))


@bp.route("/api/state")
def api_state():
    """Get current pipeline state"""
    state = get_state(current_app._get_current_object())
    ps = state.pipeline_state
    return jsonify(
        {
            "has_image": ps.get("image_path") is not None,
            "has_video": ps.get("video_path") is not None,
            "has_overlay": ps.get("text_overlay_path") is not None,
            "has_final": ps.get("final_video_path") is not None,
            "video_title": ps.get("video_title"),
        }
    )


@bp.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset pipeline state"""
    state = get_state(current_app._get_current_object())
    state.pipeline_state.clear()
    state.pipeline_state.update(
        {
            "image_path": None,
            "video_path": None,
            "video_title": None,
            "text_overlay_path": None,
            "final_video_path": None,
        }
    )
    return jsonify({"success": True, "message": "Pipeline state reset"})


@bp.route("/api/reset-downloaded-videos", methods=["POST"])
def api_reset_downloaded_videos():
    """Clear downloaded video IDs tracking list"""
    try:
        downloaded_file = Path("assets/downloaded_videos.txt")
        downloaded_file.parent.mkdir(parents=True, exist_ok=True)
        downloaded_file.write_text("", encoding="utf-8")
        return jsonify({"success": True, "message": "Downloaded videos list has been reset"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@bp.route("/api/stop-all", methods=["POST"])
def api_stop_all():
    """Stop all running processes"""
    try:
        state = get_state(current_app._get_current_object())
        state.stop_event.set()
        return jsonify({"success": True, "message": "Stop signal sent to all running processes"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
