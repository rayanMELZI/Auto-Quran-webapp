import logging
import os
import subprocess
from datetime import datetime
from threading import Thread

import imageio_ffmpeg
from flask import Blueprint, current_app, jsonify, request

from logic.scripts.post_to_instagram import post_to_instagram
from services.pipeline_runtime import get_state
from services.settings import load_settings

logger = logging.getLogger(__name__)

bp = Blueprint("instagram", __name__)


def _run_post_background(app, final_video_path: str, caption: str, thumbnail_path: str) -> None:
    with app.app_context():
        out = post_to_instagram(
            video_path=final_video_path,
            caption=caption,
            thumbnail_path=thumbnail_path,
        )
        if out.get("success"):
            logger.info("Instagram background upload: %s", out.get("message"))
        else:
            logger.warning(
                "Instagram background upload failed [%s]: %s",
                out.get("error_category"),
                out.get("message"),
            )


@bp.route("/api/post-instagram", methods=["POST"])
def api_post_instagram():
    """Post final video to Instagram (sync by default; optional background=true)."""
    try:
        data = request.get_json() or {}
        caption = data.get("caption", "")
        background = bool(data.get("background") or data.get("async"))

        # state = get_state(current_app._get_current_object())
        state = get_state(getattr(current_app, "_get_current_object")())
        final_video_path = state.pipeline_state.get("final_video_path")

        if not final_video_path:
            return jsonify(
                {
                    "success": False,
                    "message": "No final video available. Please create the final video first.",
                }
            ), 400

        if not caption:
            video_title = state.pipeline_state.get("video_title", "")
            if video_title:
                caption = f"{video_title}\n\n#Quran #Islam #QuranVerses #DailyReminder #Faith #Peace"
            else:
                caption = (
                    "⚠️لا تنسوا اخواننا المستضعفين بالدعاء رحمكم الله⚠️\n\n"
                    "#اكتب_شي_تؤجر_عليه #لاتنسى_ذكر_الله\n\n"
                    "#الله #اكتب_شي_تؤجر_عليه #الله_أكبر #قران_كريم #لاتنسى_ذكر_الله #تلاوات #اللهم_امين"
                )

        thumbnail_path = state.pipeline_state.get("image_path") or "assets/nature_image.jpg"
        
        # app = current_app._get_current_object()
        app = getattr(current_app, "_get_current_object")()

        if background:
            Thread(
                target=_run_post_background,
                args=(app, final_video_path, caption, thumbnail_path),
                daemon=True,
            ).start()
            return (
                jsonify(
                    {
                        "success": True,
                        "background": True,
                        "message": "Instagram upload started in the background. Check server logs for result.",
                    }
                ),
                202,
            )

        out = post_to_instagram(
            video_path=final_video_path,
            caption=caption,
            thumbnail_path=thumbnail_path,
        )

        if out.get("success"):
            return jsonify(
                {
                    "success": True,
                    "message": out.get("message", "Posted to Instagram."),
                }
            )

        status = 503 if out.get("error_category") in ("ip_block", "rate_limit", "blocked", "proxy") else 502
        return (
            jsonify(
                {
                    "success": False,
                    "message": out.get("message", "Failed to post to Instagram."),
                    "error_category": out.get("error_category"),
                }
            ),
            status,
        )
    except Exception as e:
        logger.exception("api_post_instagram")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


def _extract_cover(video_path: str, thumb_path: str) -> str:
    """Grab a frame from the video as the reel cover. clip_upload needs a real image and
    instagrapi's own extraction is unreliable for these videos. Returns '' on failure."""
    try:
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-ss", "0.5", "-i", video_path,
             "-frames:v", "1", "-q:v", "3", thumb_path],
            check=True, capture_output=True, timeout=60,
        )
        return thumb_path
    except Exception as exc:
        logger.warning("post-video: cover extraction failed: %s", exc)
        return ""


@bp.route("/api/post-video", methods=["POST"])
def api_post_video():
    """Publish an uploaded video straight to Instagram, skipping the pipeline.
    Multipart: `video` file + optional `caption`. Used by ChromaQuran, which renders
    its own video and only needs it posted."""
    try:
        file = request.files.get("video")
        if file is None or not file.filename:
            return jsonify({"success": False, "message": "No video file provided"}), 400

        caption = (request.form.get("caption") or "").strip() or load_settings()["default_caption"]

        # Unique name so concurrent posts don't clobber each other
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_dir = current_app.config["OUTPUT_DIR"]
        video_path = os.path.join(output_dir, f"external_{stamp}.mp4")
        file.save(video_path)
        thumb_path = _extract_cover(video_path, os.path.join(output_dir, f"external_{stamp}.jpg"))

        out = post_to_instagram(video_path=video_path, caption=caption, thumbnail_path=thumb_path)
        if out.get("success"):
            return jsonify({"success": True, "message": out.get("message", "Posted to Instagram.")})

        status = 503 if out.get("error_category") in ("ip_block", "rate_limit", "blocked", "proxy") else 502
        return jsonify({
            "success": False,
            "message": out.get("message", "Failed to post to Instagram."),
            "error_category": out.get("error_category"),
        }), status
    except Exception as e:
        logger.exception("api_post_video")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
