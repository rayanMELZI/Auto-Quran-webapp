import argparse
from datetime import datetime
from typing import Optional

try:
    from .create_final_video import create_final_video
    from .download_image import download_nature_image
    from .download_quran_video import download_quran_video
    from .extract_text_from_video import extract_text_from_video
    from .post_to_instagram import post_to_instagram
except ImportError:
    from create_final_video import create_final_video
    from download_image import download_nature_image
    from download_quran_video import download_quran_video
    from extract_text_from_video import extract_text_from_video
    from post_to_instagram import post_to_instagram


DEFAULT_CAPTION = (
    "⚠️لا تنسوا اخواننا المستضعفين بالدعاء رحمكم الله⚠️\n\n"
    "#اكتب_شي_تؤجر_عليه #لاتنسى_ذكر_الله\n\n"
    "#الله #اكتب_شي_تؤجر_عليه #الله_أكبر #قران_كريم #لاتنسى_ذكر_الله #تلاوات #اللهم_امين"
)


def build_caption(video_title: Optional[str] = None, custom_caption: Optional[str] = None) -> str:
    if custom_caption:
        return custom_caption
    if video_title:
        return f"{video_title}\n\n#Quran #Islam #QuranVerses #DailyReminder #Faith #Peace"
    return DEFAULT_CAPTION


def create_and_post_quran_content(
    post: bool = True,
    custom_caption: Optional[str] = None,
    use_text_overlay: bool = True,
    channel_url: str = "https://www.youtube.com/@Am9li9/videos",
    keyword: str = "سورة",
    video_url: Optional[str] = None,
) -> bool:
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Starting Quran content creation process - {current_date}")

    image_path = download_nature_image()
    if not image_path:
        print("Image step failed.")
        return False

    quran_video_path, video_title, video_meta = download_quran_video(
        channel_url=channel_url,
        title_keyword=keyword,
        video_url=video_url,
    )
    if not quran_video_path:
        message = video_meta.get("message") if isinstance(video_meta, dict) else None
        if message:
            print(message)
        print("Video download step failed.")
        return False

    text_frame_path = None
    if use_text_overlay:
        text_frame_path = extract_text_from_video(quran_video_path)
        if not text_frame_path:
            print("Text extraction failed. Continuing without text overlay.")

    final_video_path = create_final_video(image_path, quran_video_path, text_frame_path)
    if not final_video_path:
        print("Final video creation failed.")
        return False

    if not post:
        print(f"Pipeline completed without posting. Final video: {final_video_path}")
        return True

    caption = build_caption(video_title=video_title, custom_caption=custom_caption)
    success = post_to_instagram(final_video_path, caption)

    if success:
        print("Daily Quran post completed successfully!")
    else:
        print("Failed during Instagram post step.")

    return success


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Auto Quran full pipeline.")
    parser.add_argument("--no-post", action="store_true", help="Generate final video only, do not post to Instagram")
    parser.add_argument("--caption", default=None, help="Custom Instagram caption")
    parser.add_argument("--no-overlay", action="store_true", help="Skip text-overlay extraction step")
    parser.add_argument("--channel-url", default="https://www.youtube.com/@Am9li9/videos", help="YouTube channel URL")
    parser.add_argument("--keyword", default="سورة", help="Keyword filter used with channel URL")
    parser.add_argument("--video-url", default=None, help="Optional direct YouTube video URL")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    ok = create_and_post_quran_content(
        post=not args.no_post,
        custom_caption=args.caption,
        use_text_overlay=not args.no_overlay,
        channel_url=args.channel_url,
        keyword=args.keyword,
        video_url=args.video_url,
    )
    if not ok:
        raise SystemExit(1)