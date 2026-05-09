import time
from copy import deepcopy
from datetime import datetime
from threading import Event, Lock
from typing import Any, Dict, Optional

from pathlib import Path

from flask import Flask

from logic.scripts.create_final_video import create_final_video
from logic.scripts.download_image import download_nature_image
from logic.scripts.download_quran_video import download_quran_video
from logic.scripts.extract_text_from_video import extract_text_from_video
from logic.scripts.post_to_instagram import post_to_instagram
from services.settings import load_settings

STATE_KEY = "autoquran_state"


class AppState:
    def __init__(self) -> None:
        self.pipeline_state: Dict[str, Optional[str]] = {
            "image_path": None,
            "video_path": None,
            "video_title": None,
            "text_overlay_path": None,
            "final_video_path": None,
        }
        self.progress_lock = Lock()
        self.stop_event = Event()
        self.progress_state = new_progress_state()


def new_progress_state():
    return {
        "active": False,
        "mode": None,
        "overall_percent": 0.0,
        "overall_message": "",
        "current_step": None,
        "step_order": [],
        "steps": {},
    }


def get_state(app: Flask) -> AppState:
    return app.extensions[STATE_KEY]


def recalculate_overall_locked(state: AppState) -> None:
    progress_state = state.progress_state
    step_order = progress_state.get("step_order", [])
    if not step_order:
        progress_state["overall_percent"] = 0.0
        return

    total = len(step_order)
    score = 0.0

    for step in step_order:
        data = progress_state["steps"].get(step, {})
        status = data.get("status")
        if status in ("completed", "skipped"):
            score += 1.0
        elif status == "processing":
            score += max(0.0, min(100.0, float(data.get("progress", 0.0)))) / 100.0

    progress_state["overall_percent"] = round((score / total) * 100.0, 1)


def reset_progress(app: Flask, mode, step_order) -> None:
    state = get_state(app)
    with state.progress_lock:
        state.progress_state.clear()
        state.progress_state.update(new_progress_state())
        state.progress_state["active"] = True
        state.progress_state["mode"] = mode
        state.progress_state["step_order"] = list(step_order)
        state.progress_state["steps"] = {
            step: {
                "status": "pending",
                "progress": 0.0,
                "message": "",
                "result": None,
            }
            for step in step_order
        }
        recalculate_overall_locked(state)


def set_step(app: Flask, step, *, status=None, progress=None, message=None, result=None):
    state = get_state(app)
    with state.progress_lock:
        ps = state.progress_state
        if step not in ps.get("steps", {}):
            ps["steps"][step] = {
                "status": "pending",
                "progress": 0.0,
                "message": "",
                "result": None,
            }
            ps["step_order"].append(step)

        data = ps["steps"][step]
        if status is not None:
            data["status"] = status
        if progress is not None:
            data["progress"] = round(max(0.0, min(100.0, float(progress))), 1)
        if message is not None:
            data["message"] = message
        if result is not None:
            data["result"] = result

        ps["current_step"] = step
        if message:
            ps["overall_message"] = message

        recalculate_overall_locked(state)


def finalize_progress(app: Flask, message: str = "Done") -> None:
    state = get_state(app)
    with state.progress_lock:
        ps = state.progress_state
        ps["active"] = False
        ps["current_step"] = None
        ps["overall_message"] = message
        recalculate_overall_locked(state)


def progress_snapshot(app: Flask) -> Dict[str, Any]:
    state = get_state(app)
    with state.progress_lock:
        return deepcopy(state.progress_state)


def run_full_pipeline_bg(
    app: Flask,
    skip_text_overlay,
    auto_post,
    caption,
    channel_url,
    keyword,
    video_url,
    max_video_duration_seconds=None,
) -> None:
    """Background task for full pipeline execution (requires Flask app context)."""
    with app.app_context():
        _run_full_pipeline_bg_impl(
            app,
            skip_text_overlay,
            auto_post,
            caption,
            channel_url,
            keyword,
            video_url,
            max_video_duration_seconds,
        )


def _run_full_pipeline_bg_impl(
    app: Flask,
    skip_text_overlay,
    auto_post,
    caption,
    channel_url,
    keyword,
    video_url,
    max_video_duration_seconds,
) -> None:
    state = get_state(app)
    step_order = ["image", "video", "overlay", "final"] + (["post"] if auto_post else [])
    reset_progress(app, "full-pipeline", step_order)

    try:
        if state.stop_event.is_set():
            finalize_progress(app, "Pipeline cancelled by user")
            return

        set_step(app, "image", status="processing", progress=0, message="Downloading image...")

        settings = load_settings()
        default_image = settings.get("default_image_path")

        if default_image and Path(default_image).exists():
            image_path = default_image
            print(f"Using default image: {image_path}")
        else:
            image_path = download_nature_image()

        if not image_path:
            set_step(app, "image", status="error", message="Failed to download image")
            finalize_progress(app, "Pipeline failed at image step")
            return
        state.pipeline_state["image_path"] = image_path
        image_result = {
            "step": "image",
            "success": True,
            "message": "Image downloaded successfully",
            "preview_url": "/api/preview/image",
        }
        set_step(
            app,
            "image",
            status="completed",
            progress=100,
            message=image_result["message"],
            result=image_result,
        )

        if state.stop_event.is_set():
            finalize_progress(app, "Pipeline cancelled by user")
            return

        set_step(app, "video", status="processing", progress=0, message="Downloading video...")
        video_path, video_title, video_meta = download_quran_video(
            channel_url=channel_url,
            title_keyword=keyword,
            video_url=video_url,
            max_duration_seconds=max_video_duration_seconds,
        )
        if not video_path:
            video_error = (
                video_meta.get("message")
                if isinstance(video_meta, dict)
                else "Failed to download video"
            )
            set_step(app, "video", status="error", message=video_error)
            finalize_progress(app, "Pipeline failed at video step")
            return
        state.pipeline_state["video_path"] = video_path
        state.pipeline_state["video_title"] = video_title
        video_result = {
            "step": "video",
            "success": True,
            "message": f"Video downloaded: {video_title}",
            "preview_url": "/api/preview/video",
        }
        set_step(
            app,
            "video",
            status="completed",
            progress=100,
            message=video_result["message"],
            result=video_result,
        )

        if state.stop_event.is_set():
            finalize_progress(app, "Pipeline cancelled by user")
            return

        text_overlay_path = None
        if not skip_text_overlay:
            set_step(
                app,
                "overlay",
                status="processing",
                progress=0,
                message="Extracting text overlay...",
            )
            text_overlay_path = extract_text_from_video(video_path)
            if text_overlay_path:
                state.pipeline_state["text_overlay_path"] = text_overlay_path
                overlay_result = {
                    "step": "overlay",
                    "success": True,
                    "message": "Text overlay extracted successfully",
                    "preview_url": "/api/preview/overlay",
                }
                set_step(
                    app,
                    "overlay",
                    status="completed",
                    progress=100,
                    message=overlay_result["message"],
                    result=overlay_result,
                )
            else:
                state.pipeline_state["text_overlay_path"] = None
                overlay_result = {
                    "step": "overlay",
                    "success": False,
                    "message": "Text overlay extraction failed. Continuing without overlay.",
                }
                set_step(
                    app,
                    "overlay",
                    status="error",
                    progress=100,
                    message=overlay_result["message"],
                    result=overlay_result,
                )
                text_overlay_path = None
        else:
            overlay_result = {
                "step": "overlay",
                "success": True,
                "message": "Overlay step skipped by user option",
            }
            set_step(
                app,
                "overlay",
                status="skipped",
                progress=100,
                message=overlay_result["message"],
                result=overlay_result,
            )

        if state.stop_event.is_set():
            finalize_progress(app, "Pipeline cancelled by user")
            return

        set_step(app, "final", status="processing", progress=0, message="Creating final video...")
        final_video_path = create_final_video(
            image_path,
            video_path,
            text_overlay_path,
            progress_callback=lambda percent, msg: set_step(
                app, "final", status="processing", progress=percent, message=msg
            ),
        )
        if not final_video_path:
            set_step(app, "final", status="error", message="Failed to create final video")
            finalize_progress(app, "Pipeline failed at final step")
            return
        state.pipeline_state["final_video_path"] = final_video_path
        final_result = {
            "step": "final",
            "success": True,
            "message": "Final video created successfully",
            "preview_url": "/api/preview/final",
        }
        set_step(
            app,
            "final",
            status="completed",
            progress=100,
            message=final_result["message"],
            result=final_result,
        )

        if auto_post:
            if state.stop_event.is_set():
                finalize_progress(app, "Pipeline cancelled by user")
                return

            set_step(
                app,
                "post",
                status="processing",
                progress=0,
                message="Posting to Instagram...",
            )
            if not caption:
                caption = (
                    f"{video_title}\n\n#Quran #Islam #QuranVerses"
                    if video_title
                    else "Daily Quran verse"
                )

            post_out = post_to_instagram(
                final_video_path,
                caption,
                state.pipeline_state.get("image_path") or "assets/nature_image.jpg",
            )
            if not post_out.get("success"):
                # Non-fatal: video is ready; Instagram often fails on IP / rate limits
                post_result = {
                    "step": "post",
                    "success": False,
                    "message": post_out.get("message", "Instagram upload failed."),
                    "error_category": post_out.get("error_category"),
                }
                set_step(
                    app,
                    "post",
                    status="completed",
                    progress=100,
                    message=post_result["message"],
                    result=post_result,
                )
                finalize_progress(
                    "Pipeline completed successfully (video ready; Instagram upload failed — see server logs)"
                )
                return
            post_result = {
                "step": "post",
                "success": True,
                "message": post_out.get("message", "Video posted to Instagram successfully"),
            }
            set_step(
                app,
                "post",
                status="completed",
                progress=100,
                message=post_result["message"],
                result=post_result,
            )

        finalize_progress(app, "Pipeline completed successfully")
    except Exception as e:
        print(f"Background pipeline error: {e}")
        finalize_progress(app, f"Pipeline failed: {str(e)}")


def scheduled_pipeline_job(app: Flask) -> None:
    """Scheduled cronjob that runs the pipeline automatically."""
    print(f"[CRONJOB] Starting scheduled pipeline at {datetime.now()}")
    settings = load_settings()

    channel_url = settings.get("default_channel_url", "https://www.youtube.com/@Am9li9/videos")
    keyword = settings.get("default_keyword", "سورة")
    caption = settings.get("default_caption", "")

    max_retries = 5
    retry_count = 0
    start_date = datetime.now().date()
    state = get_state(app)

    while retry_count < max_retries:
        if datetime.now().date() != start_date:
            print("[CRONJOB] Day changed, stopping retries for previous day")
            break

        if retry_count > 0:
            print(f"[CRONJOB] Retry attempt {retry_count}/{max_retries}")

        try:
            state.stop_event.clear()
            run_full_pipeline_bg(
                app,
                skip_text_overlay=False,
                auto_post=True,
                caption=caption,
                channel_url=channel_url,
                keyword=keyword,
                video_url=None,
                max_video_duration_seconds=None,
            )

            with state.progress_lock:
                if state.progress_state.get("overall_percent") == 100.0:
                    print("[CRONJOB] Pipeline completed successfully")
                    return
        except Exception as e:
            print(f"[CRONJOB] Pipeline failed with error: {e}")

        retry_count += 1
        if retry_count < max_retries:
            time.sleep(300)

    print(f"[CRONJOB] Pipeline failed after {retry_count} attempts")
