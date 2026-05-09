from flask import Blueprint, current_app, jsonify, request

from logic.scripts.post_to_instagram import post_to_instagram
from services.pipeline_runtime import get_state

bp = Blueprint("instagram", __name__)


@bp.route("/api/post-instagram", methods=["POST"])
def api_post_instagram():
    """Post final video to Instagram"""
    try:
        data = request.get_json() or {}
        caption = data.get("caption", "")

        state = get_state(current_app._get_current_object())
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

        success = post_to_instagram(
            video_path=final_video_path,
            caption=caption,
            thumbnail_path=thumbnail_path,
        )

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "Video posted to Instagram successfully! 🎉",
                }
            )
        return jsonify({"success": False, "message": "Failed to post to Instagram"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
