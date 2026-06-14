import logging
from threading import Thread

from flask import Blueprint, current_app, jsonify, request

from logic.scripts.post_to_instagram import post_to_instagram
from services.pipeline_runtime import get_state

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
