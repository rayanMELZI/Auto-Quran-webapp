import argparse
import random
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, cast

import imageio_ffmpeg
import yt_dlp


def _load_downloaded_ids(file_path: Path) -> Set[str]:
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        return set()

    with open(file_path, "r", encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip()}


def _append_downloaded_id(file_path: Path, video_id: str) -> None:
    with open(file_path, "a", encoding="utf-8") as handle:
        handle.write(f"{video_id}\n")


def _normalize_video_url(entry: Dict[str, Any]) -> Optional[str]:
    url = entry.get("webpage_url") or entry.get("url")
    if not url:
        video_id = entry.get("id")
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else None

    if isinstance(url, str) and url.startswith("http"):
        return url

    return f"https://www.youtube.com/watch?v={entry.get('id')}"


def _build_meta(
    *,
    video_id: Optional[str] = None,
    source_type: str = "channel",
    duplicate: bool = False,
    message: str = "",
) -> Dict[str, object]:
    return {
        "video_id": video_id,
        "source_type": source_type,
        "duplicate": duplicate,
        "message": message,
    }


def download_quran_video(
    channel_url: str = "https://www.youtube.com/@Am9li9/videos",
    output_path: str = "assets/quran_video.mp4",
    downloaded_videos_file: str = "assets/downloaded_videos.txt",
    title_keyword: str = "سورة",
    video_url: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Dict[str, object]]:
    print("Downloading Quran video...")

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    downloaded_file = Path(downloaded_videos_file).resolve()

    downloaded_ids = _load_downloaded_ids(downloaded_file)

    info_opts: Dict[str, Any] = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "ignoreerrors": True,
    }

    selected: Optional[Dict[str, Any]] = None
    source_type = "video" if video_url else "channel"

    if video_url:
        try:
            video_info_opts: Dict[str, Any] = {"quiet": True, "skip_download": True, "ignoreerrors": True}
            with yt_dlp.YoutubeDL(cast(Any, video_info_opts)) as ydl:
                selected = cast(Dict[str, Any], ydl.extract_info(video_url, download=False))
        except Exception as exc:
            print(f"Failed to read YouTube video info: {exc}")
            return None, None, _build_meta(
                source_type=source_type,
                message=f"Failed to read YouTube video info: {exc}",
            )

        if not selected or not selected.get("id"):
            return None, None, _build_meta(
                source_type=source_type,
                message="Could not resolve selected video details.",
            )
    else:
        try:
            with yt_dlp.YoutubeDL(cast(Any, info_opts)) as ydl:
                channel_info = ydl.extract_info(channel_url, download=False)
        except Exception as exc:
            print(f"Failed to read YouTube channel info: {exc}")
            return None, None, _build_meta(
                source_type=source_type,
                message=f"Failed to read YouTube channel info: {exc}",
            )

        entries = [e for e in channel_info.get("entries", []) if e and e.get("id") and e.get("title")]
        keyword_entries = [e for e in entries if title_keyword in e.get("title", "")]

        if not keyword_entries:
            print(f"No videos found with keyword '{title_keyword}'.")
            return None, None, _build_meta(
                source_type=source_type,
                message=f"No videos found with keyword '{title_keyword}'.",
            )

        new_entries = [e for e in keyword_entries if e["id"] not in downloaded_ids]
        if not new_entries:
            return None, None, _build_meta(
                source_type=source_type,
                duplicate=True,
                message="All matching videos are already downloaded. Change keyword/channel or clear assets/downloaded_videos.txt.",
            )

        selected = random.choice(new_entries)

    if selected is None:
        return None, None, _build_meta(
            source_type=source_type,
            message="No video was selected for download.",
        )

    selected_id = selected.get("id")
    if not selected_id:
        return None, None, _build_meta(
            source_type=source_type,
            message="Selected video has no valid ID.",
        )

    is_new = selected_id not in downloaded_ids
    if not is_new:
        return None, None, _build_meta(
            video_id=selected_id,
            source_type=source_type,
            duplicate=True,
            message="Selected video is already downloaded. Pick another video/channel.",
        )

    resolved_video_url = _normalize_video_url(selected)
    if not resolved_video_url:
        print("Could not resolve selected video URL.")
        return None, None, _build_meta(
            video_id=selected_id,
            source_type=source_type,
            message="Could not resolve selected video URL.",
        )

    if output.exists():
        output.unlink()

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    dl_opts: Dict[str, Any] = {
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(output),
        "overwrites": True,
        "nopart": True,
        "noplaylist": True,
        "ffmpeg_location": ffmpeg_path,
        "quiet": False,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(cast(Any, dl_opts)) as ydl:
            ydl.download([resolved_video_url])
    except Exception as exc:
        print(f"Error downloading selected video: {exc}")
        return None, None, _build_meta(
            video_id=selected_id,
            source_type=source_type,
            message=f"Error downloading selected video: {exc}",
        )

    if is_new:
        _append_downloaded_id(downloaded_file, selected_id)

    title = selected.get("title")
    print(f"Downloaded: {title} -> {output}")
    return str(output), title, _build_meta(
        video_id=selected_id,
        source_type=source_type,
        duplicate=False,
        message="Video downloaded successfully.",
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download a Quran video from a YouTube channel.")
    parser.add_argument("--channel-url", default="https://www.youtube.com/@Am9li9/videos", help="YouTube channel videos URL")
    parser.add_argument("--output", default="assets/quran_video.mp4", help="Output video path")
    parser.add_argument("--downloaded-file", default="assets/downloaded_videos.txt", help="File to track downloaded video IDs")
    parser.add_argument("--keyword", default="سورة", help="Keyword that must exist in the title")
    parser.add_argument("--video-url", default=None, help="Optional direct YouTube video URL")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    video_path, video_title, meta = download_quran_video(
        channel_url=args.channel_url,
        output_path=args.output,
        downloaded_videos_file=args.downloaded_file,
        title_keyword=args.keyword,
        video_url=args.video_url,
    )
    if not video_path:
        if meta.get("message"):
            print(meta["message"])
        raise SystemExit(1)
    print(video_path)
    if video_title:
        print(video_title)