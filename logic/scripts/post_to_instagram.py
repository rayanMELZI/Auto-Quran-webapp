import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired


def post_to_instagram(
    video_path: str,
    caption: str,
    thumbnail_path: str = "assets/nature_image.jpg",
    session_file: str = "instagram_session.json",
) -> bool:
    print("Posting to Instagram...")

    load_dotenv()
    username = os.getenv("INSTA_USERNAME")
    password = os.getenv("INSTA_PASSWORD")

    if not username or not password:
        print("Instagram credentials are missing in .env (INSTA_USERNAME, INSTA_PASSWORD).")
        return False

    if not Path(video_path).exists():
        print(f"Video file not found: {video_path}")
        return False

    thumb = thumbnail_path if Path(thumbnail_path).exists() else None

    try:
        cl = Client()

        if Path(session_file).exists():
            try:
                cl.load_settings(session_file)
                cl.get_timeline_feed()
                print("Loaded existing Instagram session.")
            except LoginRequired:
                print("Session expired, logging in again.")
                cl.login(username, password)
                cl.dump_settings(session_file)
        else:
            cl.login(username, password)
            cl.dump_settings(session_file)

        media = cl.clip_upload(
            video_path,
            caption=caption,
            thumbnail=thumb,
            extra_data={
                "custom_accessibility_caption": "Quran Verse",
                "like_and_view_counts_disabled": False,
                "disable_comments": False,
            },
        )

        print(f"Successfully posted. Media ID: {media.id}")
        return True
    except Exception as exc:
        print(f"Error posting to Instagram: {exc}")
        return False


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload a video reel to Instagram.")
    parser.add_argument("video_path", help="Path to the final video")
    parser.add_argument("caption", help="Caption text")
    parser.add_argument("--thumbnail", default="assets/nature_image.jpg", help="Thumbnail image path")
    parser.add_argument("--session-file", default="instagram_session.json", help="Path to session json")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    success = post_to_instagram(
        video_path=args.video_path,
        caption=args.caption,
        thumbnail_path=args.thumbnail,
        session_file=args.session_file,
    )
    if not success:
        raise SystemExit(1)