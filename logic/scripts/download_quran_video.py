import argparse
import os
import random
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, cast

import imageio_ffmpeg
import yt_dlp


def _get_common_ydl_opts() -> Dict[str, Any]:
    """Get common yt-dlp options to bypass bot detection."""
    opts: Dict[str, Any] = {
        "nocheckcertificate": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }

    # Optional cookie support (disabled by default for cloud hosts like Render).
    # Set YTDLP_COOKIES_FILE to a netscape cookie file path, or
    # YTDLP_COOKIES_FROM_BROWSER to browser name (e.g. chrome, firefox, edge).
    cookie_file = os.getenv("YTDLP_COOKIES_FILE", "").strip()
    browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER", "").strip().lower()

    if cookie_file:
        opts["cookiefile"] = cookie_file
    elif browser:
        opts["cookiesfrombrowser"] = (browser,)

    return opts


def _can_retry_without_cookies(exc: Exception, opts: Dict[str, Any]) -> bool:
    message = str(exc).lower()
    has_cookie_opts = "cookiesfrombrowser" in opts or "cookiefile" in opts
    cookie_error_markers = [
        "failed to load cookies",
        "could not find chrome cookies database",
        "could not find firefox cookies database",
        "could not find edge cookies database",
    ]
    return has_cookie_opts and any(marker in message for marker in cookie_error_markers)


def _extract_info_with_fallback(url: str, opts: Dict[str, Any]) -> Dict[str, Any]:
    try:
        with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
            return cast(Dict[str, Any], ydl.extract_info(url, download=False))
    except Exception as exc:
        if not _can_retry_without_cookies(exc, opts):
            raise
        retry_opts = dict(opts)
        retry_opts.pop("cookiesfrombrowser", None)
        retry_opts.pop("cookiefile", None)
        print("Cookie loading failed. Retrying YouTube request without cookies.")
        with yt_dlp.YoutubeDL(cast(Any, retry_opts)) as ydl:
            return cast(Dict[str, Any], ydl.extract_info(url, download=False))


def _download_with_fallback(url: str, opts: Dict[str, Any]) -> None:
    try:
        with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
            ydl.download([url])
    except Exception as exc:
        if not _can_retry_without_cookies(exc, opts):
            raise
        retry_opts = dict(opts)
        retry_opts.pop("cookiesfrombrowser", None)
        retry_opts.pop("cookiefile", None)
        print("Cookie loading failed. Retrying download without cookies.")
        with yt_dlp.YoutubeDL(cast(Any, retry_opts)) as ydl:
            ydl.download([url])


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
        **_get_common_ydl_opts(),
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "ignoreerrors": True,
    }

    selected: Optional[Dict[str, Any]] = None
    source_type = "video" if video_url else "channel"

    if video_url:
        try:
            video_info_opts: Dict[str, Any] = {
                **_get_common_ydl_opts(),
                "quiet": True,
                "skip_download": True,
                "ignoreerrors": True,
            }
            selected = _extract_info_with_fallback(video_url, video_info_opts)
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
            channel_info = _extract_info_with_fallback(channel_url, info_opts)
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
    
    # Download video and audio separately, then merge with full control
    temp_video = output.parent / f"{output.stem}_video.mp4"
    temp_audio = output.parent / f"{output.stem}_audio.m4a"
    
    try:
        # Download video only
        video_opts: Dict[str, Any] = {
            **_get_common_ydl_opts(),
            "format": "bestvideo[ext=mp4]/bestvideo",
            "outtmpl": str(temp_video),
            "quiet": True,
            "no_warnings": True,
        }
        _download_with_fallback(resolved_video_url, video_opts)
        
        # Download audio only
        audio_opts: Dict[str, Any] = {
            **_get_common_ydl_opts(),
            "format": "bestaudio[ext=m4a]/bestaudio",
            "outtmpl": str(temp_audio),
            "quiet": True,
            "no_warnings": True,
        }
        _download_with_fallback(resolved_video_url, audio_opts)
        
        # Manually merge with FFmpeg
        import subprocess
        merge_cmd = [
            ffmpeg_path,
            "-i", str(temp_video),
            "-i", str(temp_audio),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-strict", "experimental",
            str(output),
            "-y"
        ]
        
        result = subprocess.run(merge_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg merge error: {result.stderr}")
            raise Exception("Failed to merge video and audio")
        
        # Clean up temp files
        if temp_video.exists():
            temp_video.unlink()
        if temp_audio.exists():
            temp_audio.unlink()
            
    except Exception as exc:
        # Clean up temp files on error
        if temp_video.exists():
            temp_video.unlink()
        if temp_audio.exists():
            temp_audio.unlink()
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