"""
Download Quran videos using Invidious (free YouTube alternative) with YouTube fallback.
Works on Render with fallback to direct YouTube if Invidious is unavailable.
"""

import os
import random
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple
from urllib.parse import quote

import requests
import yt_dlp


# Invidious public instances (try multiple for redundancy)
# Prioritize snopyta.org which is most reliable
INVIDIOUS_INSTANCES = [
    "https://invidious.snopyta.org",
    "https://inv.nadeko.net",
    "https://invidious.io",
    "https://yewtu.be",
    "https://invidious.projectsegfau.lt",
]

# Current instance
_CURRENT_INSTANCE = INVIDIOUS_INSTANCES[0]


def _apply_optional_youtube_cookies(opts: Dict[str, Any]) -> Dict[str, Any]:
    """Attach cookiefile to yt-dlp options when YOUTUBE_COOKIES env var is set."""
    cookies_text = os.getenv("YOUTUBE_COOKIES")
    if not cookies_text:
        return opts

    cookie_path = Path("assets/youtube_cookies.txt").resolve()
    cookie_path.parent.mkdir(parents=True, exist_ok=True)

    # Support both real newlines and escaped \n sequences from env vars.
    normalized = cookies_text.replace("\\r\\n", "\n").replace("\\n", "\n")
    with open(cookie_path, "w", encoding="utf-8") as handle:
        handle.write(normalized)

    opts["cookiefile"] = str(cookie_path)
    return opts


def _get_working_instance() -> str:
    """Find a working Invidious instance."""
    global _CURRENT_INSTANCE
    
    for instance in INVIDIOUS_INSTANCES:
        try:
            resp = requests.get(f"{instance}/api/v1/stats", timeout=5)
            if resp.status_code == 200:
                print(f"[INVIDIOUS] Using instance: {instance}")
                _CURRENT_INSTANCE = instance
                return instance
        except:
            continue
    
    # Fallback to first instance
    print(f"[INVIDIOUS] Using fallback instance: {INVIDIOUS_INSTANCES[0]}")
    return INVIDIOUS_INSTANCES[0]


def _extract_channel_id(channel_url: str) -> Optional[str]:
    """Extract channel ID from YouTube URL."""
    # Format: https://www.youtube.com/@ChannelName or https://www.youtube.com/@ChannelName/videos
    if "@" in channel_url:
        channel_handle = channel_url.split("@")[-1].rstrip("/").rstrip("videos").rstrip("/")
        return channel_handle
    return None


def _get_channel_videos(channel_identifier: str, timeout_seconds: int = 20) -> Dict[str, Any]:
    """Get channel videos from Invidious API with timeout."""
    result: Dict[str, Any] = {}
    error: Optional[Exception] = None

    def fetch_worker():
        nonlocal result, error
        try:
            instance = _get_working_instance()
            # Search for channel
            url = f"{instance}/api/v1/channels/{channel_identifier}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            result = resp.json()
        except Exception as exc:
            error = exc

    thread = threading.Thread(target=fetch_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        raise TimeoutError(f"Invidious channel fetch timed out after {timeout_seconds}s")
    
    if error:
        raise error
    
    return result


def _search_youtube_fallback(keyword: str, timeout_seconds: int = 20) -> list:
    """Fallback search using yt-dlp directly on YouTube."""
    result: list = []
    error: Optional[Exception] = None
    
    def youtube_worker():
        nonlocal result, error
        try:
            print("[YOUTUBE_FALLBACK] Attempting YouTube search...")
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch',
                'socket_timeout': 20,
                'ignoreerrors': True,
                'extract_flat': True,
                'skip_download': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'tv_embedded', 'web']
                    }
                },
            }
            ydl_opts = _apply_optional_youtube_cookies(ydl_opts)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch20:{keyword}", download=False)
                if info and 'entries' in info:
                    result = [
                        {
                            'videoId': entry.get('id'),
                            'title': entry.get('title', 'Unknown'),
                            'author': entry.get('uploader', 'Unknown'),
                        }
                        for entry in info['entries']
                        if entry and entry.get('id')
                    ][:20]
                    if result:
                        print(f"[YOUTUBE_FALLBACK] Found {len(result)} videos on YouTube")
                        return
        except Exception as e:
            print(f"[YOUTUBE_FALLBACK] Failed: {str(e)[:50]}")
            error = e
    
    thread = threading.Thread(target=youtube_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        print("[YOUTUBE_FALLBACK] Timeout")
        return []
    
    return result


def _search_channel_videos(channel_handle: str, keyword: str, timeout_seconds: int = 20) -> list:
    """Search for videos in channel by keyword using Invidious, with YouTube fallback."""
    result: list = []
    error: Optional[Exception] = None
    
    # Try all instances for search
    instances_to_try = INVIDIOUS_INSTANCES + ["https://invidious.projectsegfau.lt"]

    def search_worker():
        nonlocal result, error
        for instance in instances_to_try:
            try:
                search_url = f"{instance}/api/v1/search?q={quote(keyword)}&type=video"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                print(f"[INVIDIOUS] Trying {instance}...")
                resp = requests.get(search_url, timeout=8, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                videos = data.get("items", [])
                
                if videos:
                    result = videos[:20]
                    print(f"[INVIDIOUS] Success! Found {len(result)} videos on {instance}")
                    return
            except Exception as e:
                print(f"[INVIDIOUS] {instance} failed: {str(e)[:50]}")
                error = e
                continue

    thread = threading.Thread(target=search_worker, daemon=True)
    thread.start()
    thread.join(timeout=max(5, timeout_seconds - 15))  # Reserve time for fallback

    # If Invidious succeeded, return
    if result:
        return result
    
    # Try YouTube fallback if all Invidious instances failed
    print("[SEARCH] All Invidious instances failed, trying YouTube fallback...")
    youtube_result = _search_youtube_fallback(keyword, timeout_seconds=15)
    if youtube_result:
        return youtube_result
    
    # Both failed
    if error:
        raise error
    raise Exception("All Invidious instances and YouTube fallback failed")


def _download_video_direct(video_id: str, output_path: Path, timeout_seconds: int = 60) -> None:
    """Download video from YouTube first, fallback to Invidious."""
    youtube_error: Optional[Exception] = None
    
    # Try YouTube first (works best when YOUTUBE_COOKIES is configured)
    def youtube_download_worker():
        nonlocal youtube_error
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            opts = {
                "format": "best",
                "outtmpl": str(output_path),
                "quiet": False,
                "no_warnings": False,
                "socket_timeout": 15,
                "noplaylist": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "tv_embedded", "web"]
                    }
                },
            }
            
            opts = _apply_optional_youtube_cookies(opts)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([video_url])
                print(f"[YOUTUBE] Successfully downloaded {video_id}")
                return  # Success, exit
        except Exception as exc:
            youtube_error = exc

    thread = threading.Thread(target=youtube_download_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds // 2)

    # If YouTube succeeded (file exists), we're done
    if output_path.exists() and output_path.stat().st_size > 0:
        return
    
    # If thread is still running, proceed to fallback
    if thread.is_alive():
        print("[DOWNLOAD] YouTube taking too long, trying Invidious fallback...")
    
    # Try Invidious fallback
    print(f"[INVIDIOUS] Trying Invidious fallback download for {video_id}...")
    invidious_error: Optional[Exception] = None
    
    def invidious_download_worker():
        nonlocal invidious_error
        try:
            instance = _get_working_instance()
            video_url = f"{instance}/watch?v={video_id}"
            
            opts = {
                "format": "best",
                "outtmpl": str(output_path),
                "quiet": False,
                "no_warnings": False,
                "socket_timeout": 15,
                "noplaylist": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "tv_embedded", "web"]
                    }
                },
            }
            
            opts = _apply_optional_youtube_cookies(opts)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([video_url])
                print(f"[INVIDIOUS] Successfully downloaded {video_id} from {instance}")
        except Exception as exc:
            invidious_error = exc
    
    invidious_thread = threading.Thread(target=invidious_download_worker, daemon=True)
    invidious_thread.start()
    invidious_thread.join(timeout=timeout_seconds // 2)
    
    # Check if either method succeeded
    if output_path.exists() and output_path.stat().st_size > 0:
        return
    
    # Both failed
    if invidious_error:
        raise invidious_error
    if youtube_error:
        raise youtube_error
    
    raise TimeoutError(f"Video download timed out after {timeout_seconds}s")


def _load_downloaded_ids(file_path: Path) -> Set[str]:
    """Load set of already downloaded video IDs."""
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        return set()

    with open(file_path, "r", encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip()}


def _append_downloaded_id(file_path: Path, video_id: str) -> None:
    """Append a video ID to the downloaded list."""
    with open(file_path, "a", encoding="utf-8") as handle:
        handle.write(f"{video_id}\n")


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
    """Download Quran video using Invidious (free YouTube alternative) with fallback."""
    print("[DOWNLOAD] Starting video download...")

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    downloaded_file = Path(downloaded_videos_file).resolve()

    downloaded_ids = _load_downloaded_ids(downloaded_file)
    source_type = "video" if video_url else "channel"

    try:
        # If specific video URL provided, use it
        if video_url:
            # Extract video ID from URL
            video_id = None
            if "v=" in video_url:
                video_id = video_url.split("v=")[-1].split("&")[0]
            elif "youtube.com" in video_url or "youtu.be" in video_url:
                # Try to extract from various formats
                import re
                match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', video_url)
                if match:
                    video_id = match.group(1)
            
            if not video_id:
                return None, None, _build_meta(
                    source_type=source_type,
                    message="Could not extract video ID from URL",
                )
            
            try:
                print(f"[DOWNLOAD] Downloading video: {video_id}")
                _download_video_direct(video_id, output, timeout_seconds=60)
                _append_downloaded_id(downloaded_file, video_id)
                
                return str(output), f"Video {video_id}", _build_meta(
                    video_id=video_id,
                    source_type=source_type,
                    message="Video downloaded successfully.",
                )
            except Exception as exc:
                return None, None, _build_meta(
                    video_id=video_id,
                    source_type=source_type,
                    message=f"Error downloading video: {exc}",
                )

        # Channel mode: search for videos by keyword
        print(f"[DOWNLOAD] Searching channel for keyword: {title_keyword}")
        channel_handle = _extract_channel_id(channel_url)
        if not channel_handle:
            return None, None, _build_meta(
                source_type=source_type,
                message="Could not extract channel ID from URL",
            )

        videos = _search_channel_videos(channel_handle, title_keyword, timeout_seconds=25)
        
        if not videos:
            return None, None, _build_meta(
                source_type=source_type,
                message=f"No videos found with keyword '{title_keyword}'",
            )

        # Filter out already downloaded videos
        new_videos = [v for v in videos if v.get("videoId") not in downloaded_ids]
        
        if not new_videos:
            return None, None, _build_meta(
                source_type=source_type,
                duplicate=True,
                message="All matching videos already downloaded.",
            )

        # Pick random video from new ones
        selected = random.choice(new_videos)
        candidates = random.sample(new_videos, min(len(new_videos), 5))  # Try up to 5

        # Try to download from candidates
        for candidate in candidates:
            video_id = candidate.get("videoId")
            title = candidate.get("title", "Unknown")
            
            if not video_id or video_id in downloaded_ids:
                continue

            if output.exists():
                output.unlink()

            try:
                print(f"[DOWNLOAD] Downloading: {title} ({video_id})")
                _download_video_direct(video_id, output, timeout_seconds=60)
                _append_downloaded_id(downloaded_file, video_id)
                
                return str(output), title, _build_meta(
                    video_id=video_id,
                    source_type=source_type,
                    message="Video downloaded successfully.",
                )
            except Exception as exc:
                print(f"[DOWNLOAD] Failed for {video_id}: {exc}, trying next...")
                continue

        return None, None, _build_meta(
            source_type=source_type,
            message="Could not download any matching videos",
        )

    except TimeoutError as exc:
        return None, None, _build_meta(
            source_type=source_type,
            message=f"Timeout: {exc}",
        )
    except Exception as exc:
        return None, None, _build_meta(
            source_type=source_type,
            message=f"Error: {exc}",
        )
