"""
Download Quran videos using Invidious (free YouTube alternative) with YouTube fallback.
Works on Render with fallback to direct YouTube if Invidious is unavailable.
"""

import os
import random
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
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


def _extract_channel_handle(channel_url: str) -> Optional[str]:
    """Extract @handle, /channel/ID, or /c/custom from a YouTube channel URL."""
    if not channel_url or not str(channel_url).strip():
        return None
    try:
        from urllib.parse import urlparse, unquote

        path = unquote(urlparse(channel_url.strip()).path).strip("/")
        parts = [p for p in path.split("/") if p]
        for i, seg in enumerate(parts):
            if seg.startswith("@"):
                return seg[1:].split("/")[0]
            if seg == "channel" and i + 1 < len(parts):
                return parts[i + 1]
            if seg in ("c", "user") and i + 1 < len(parts):
                return parts[i + 1]
        return None
    except Exception:
        return None


def _ensure_channel_videos_tab_url(channel_url: str) -> str:
    """Normalize to a /videos URL for yt-dlp channel listing when possible."""
    u = channel_url.strip()
    if "/@" in u and "/videos" not in u.split("?")[0]:
        return u.rstrip("/") + "/videos"
    if "youtube.com" in u and "channel" in u and "/videos" not in u:
        return u.rstrip("/") + "/videos"
    return u


def _http_headers() -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }


def _parse_entry_duration_seconds(entry: Dict[str, Any]) -> int:
    v = entry.get("lengthSeconds")
    if v is None:
        v = entry.get("length_seconds") or entry.get("duration")
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _normalize_video_dict(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    vid = entry.get("videoId") or entry.get("video_id") or entry.get("id")
    if not vid:
        return None
    title = entry.get("title") or "Unknown"
    return {
        "videoId": vid,
        "title": title,
        "lengthSeconds": _parse_entry_duration_seconds(entry),
    }


def _title_matches_keyword(title: str, keyword: str) -> bool:
    if not (keyword or "").strip():
        return True
    kw = keyword.strip()
    return kw in (title or "")


def _duration_within_cap(length_seconds: int, max_duration_seconds: Optional[int]) -> bool:
    if not max_duration_seconds or max_duration_seconds <= 0:
        return True
    if length_seconds <= 0:
        # Unknown length: allow (Invidious often fills this); yt-dlp flat usually has duration
        return True
    if length_seconds > max_duration_seconds:
        return False
    return True


def _filter_candidates(
    videos: List[dict],
    keyword: str,
    max_duration_seconds: Optional[int],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for raw in videos:
        if not isinstance(raw, dict):
            continue
        nv = _normalize_video_dict(raw)
        if not nv:
            continue
        if not _title_matches_keyword(nv["title"], keyword):
            continue
        dur = nv["lengthSeconds"]
        if not _duration_within_cap(dur, max_duration_seconds):
            print(
                f"[FILTER] Skip (duration {dur}s > cap {max_duration_seconds}s): "
                f"{nv['title'][:80]}"
            )
            continue
        out.append(nv)
    return out


def _invidious_collect_channel_videos(channel_handle: str, timeout_seconds: int = 25) -> List[dict]:
    """Load uploads from a channel using Invidious (same channel as URL), not global search."""
    collected: List[dict] = []
    instances_to_try = list(INVIDIOUS_INSTANCES)

    for instance in instances_to_try:
        try:
            from urllib.parse import quote

            safe_handle = quote(channel_handle, safe="")
            # Channel metadata (often includes latestVideos)
            meta_url = f"{instance}/api/v1/channels/{safe_handle}"
            resp = requests.get(meta_url, timeout=10, headers=_http_headers())
            resp.raise_for_status()
            data = resp.json()
            latest = data.get("latestVideos") or []
            collected.extend(latest)

            # Paginated uploads tab
            continuation: Optional[str] = None
            for _ in range(5):
                v_url = f"{instance}/api/v1/channels/{safe_handle}/videos"
                params: Dict[str, Any] = {}
                if continuation:
                    params["continuation"] = continuation
                r2 = requests.get(v_url, params=params, timeout=12, headers=_http_headers())
                if r2.status_code != 200:
                    break
                payload = r2.json()
                if isinstance(payload, list):
                    collected.extend(payload)
                    break
                chunk = payload.get("videos") or payload.get("items") or []
                collected.extend(chunk)
                continuation = payload.get("continuation")
                if not continuation or not chunk:
                    break

            if collected:
                print(
                    f"[INVIDIOUS] Channel @{channel_handle}: collected {len(collected)} "
                    f"candidate video(s) from {instance}"
                )
                return collected
        except Exception as exc:
            print(f"[INVIDIOUS] Channel listing failed ({instance}): {str(exc)[:120]}")
            continue

    return []


def _yt_dlp_flat_channel_videos(channel_url: str, playlistend: int = 60) -> List[dict]:
    """List recent uploads from a YouTube channel URL (flat, no download)."""
    out: List[dict] = []
    tab_url = _ensure_channel_videos_tab_url(channel_url)

    def worker():
        nonlocal out
        try:
            ydl_opts: Dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "ignoreconfig": True,
                "extract_flat": "in_playlist",
                "playlistend": playlistend,
                "socket_timeout": 25,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "tv_embedded", "web"],
                    }
                },
            }
            ydl_opts = _apply_optional_youtube_cookies(ydl_opts)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(tab_url, download=False)
            entries = (info or {}).get("entries") or []
            for e in entries:
                if not e:
                    continue
                vid = e.get("id")
                if not vid:
                    continue
                title = e.get("title") or "Unknown"
                dur_raw = e.get("duration")
                try:
                    dur = int(dur_raw) if dur_raw is not None else 0
                except (TypeError, ValueError):
                    dur = 0
                out.append({"videoId": vid, "title": title, "lengthSeconds": dur})
            if out:
                print(f"[YOUTUBE] Flat-listed {len(out)} video(s) from channel tab")
        except Exception as exc:
            print(f"[YOUTUBE] Channel flat extract failed: {str(exc)[:120]}")

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=40)
    if thread.is_alive():
        print("[YOUTUBE] Channel flat listing timed out")
        return []
    return out


def _search_channel_videos(
    channel_url: str,
    channel_handle: str,
    keyword: str,
    max_duration_seconds: Optional[int],
    timeout_seconds: int = 25,
) -> list:
    """
    Videos from the given YouTube channel only, filtered by title keyword and duration cap.
    """
    raw = _invidious_collect_channel_videos(channel_handle, timeout_seconds=timeout_seconds)
    filtered = _filter_candidates(raw, keyword, max_duration_seconds)

    if filtered:
        return filtered

    print("[SEARCH] Invidious channel catalog empty after filters; trying YouTube channel tab...")
    raw_yt = _yt_dlp_flat_channel_videos(channel_url, playlistend=80)
    filtered_yt = _filter_candidates(raw_yt, keyword, max_duration_seconds)

    if filtered_yt:
        return filtered_yt

    print(
        "[SEARCH] No videos from this channel matched keyword/duration "
        "(not using global search, to avoid wrong-channel downloads)."
    )
    return []


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


def _download_video_direct(video_id: str, output_path: Path, timeout_seconds: int = 60) -> None:
    """Download video from YouTube first, fallback to Invidious."""
    youtube_error: Optional[Exception] = None
    
    # Try YouTube first (works best when YOUTUBE_COOKIES is configured)
    def youtube_download_worker():
        nonlocal youtube_error
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            opts = {
                "outtmpl": str(output_path),
                "quiet": False,
                "no_warnings": False,
                "socket_timeout": 15,
                "noplaylist": True,
                "ignoreconfig": True,
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
                "outtmpl": str(output_path),
                "quiet": False,
                "no_warnings": False,
                "socket_timeout": 15,
                "noplaylist": True,
                "ignoreconfig": True,
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


def _is_auth_challenge_error(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = [
        "sign in to confirm youre not a bot",
        "sign in to confirm you're not a bot",
        "use --cookies-from-browser or --cookies",
        "this video is age-restricted",
        "login required",
    ]
    return any(marker in message for marker in markers)


def _is_format_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "requested format is not available" in message or "no video formats found" in message


def _is_retryable_video_error(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = [
        "too many requests",
        "n challenge solving failed",
        "only images are available",
        "requested format is not available",
        "no video formats found",
    ]
    return _is_auth_challenge_error(exc) or any(marker in message for marker in markers)


def _validate_audio(video_path: str) -> Tuple[bool, str]:
    """
    Validate that the downloaded video has working audio throughout.
    Returns (is_valid, reason_message).

    Checks for:
      - Missing audio track
      - Silent / inaudible audio (all near-zero RMS)
      - White noise / static (uniform RMS with no amplitude variation)
    """
    try:
        import numpy as np
        from moviepy.editor import VideoFileClip

        with VideoFileClip(video_path) as clip:
            if clip.audio is None:
                return False, "Video has no audio track."

            duration = clip.duration
            if duration < 1.0:
                return False, "Video is too short to validate audio."

            # Sample evenly-spaced 1-second windows (1 per 30 s, clamped 3–10 windows)
            n_windows = min(10, max(3, int(duration / 30)))
            rms_values: List[float] = []
            for i in range(n_windows):
                t_start = duration * i / n_windows
                t_end = min(t_start + 1.0, duration)
                try:
                    chunk = clip.audio.subclip(t_start, t_end)
                    arr = chunk.to_soundarray(fps=4000)
                    rms = float(np.sqrt(np.mean(arr ** 2)))
                    rms_values.append(rms)
                except Exception:
                    pass

        if not rms_values:
            return False, "Could not extract audio samples from video."

        import numpy as np  # ensure available outside 'with' block
        rms_arr = np.array(rms_values)
        mean_rms = float(np.mean(rms_arr))
        std_rms = float(np.std(rms_arr))

        # Silence check: mean RMS below perceptible level
        if mean_rms < 0.01:
            return False, f"Audio is silent or inaudible (mean RMS={mean_rms:.5f})."

        # White noise / static check: real speech/recitation has clear amplitude variation;
        # static noise stays at a constant (low variation) level.
        variation_ratio = std_rms / mean_rms if mean_rms > 0 else 0.0
        if variation_ratio < 0.05:
            return False, (
                f"Audio appears to be white noise or static "
                f"(mean RMS={mean_rms:.4f}, variation ratio={variation_ratio:.3f})."
            )

        print(f"Audio validation passed (mean RMS={mean_rms:.4f}, variation={variation_ratio:.3f}).")
        return True, "Audio OK."

    except Exception as exc:
        return False, f"Audio validation error: {exc}"


def download_quran_video(
    channel_url: str = "https://www.youtube.com/@Am9li9/videos",
    output_path: str = "assets/quran_video.mp4",
    downloaded_videos_file: str = "assets/downloaded_videos.txt",
    title_keyword: str = "سورة",
    video_url: Optional[str] = None,
    max_duration_seconds: Optional[int] = None,
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

        # Channel mode: list uploads from this channel only, filter by keyword + duration
        try:
            env_cap = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", "3600"))
        except ValueError:
            env_cap = 3600
        duration_cap = env_cap if max_duration_seconds is None else max_duration_seconds
        print(
            f"[DOWNLOAD] Channel listing | keyword={title_keyword!r} | "
            f"max_duration_seconds={duration_cap}"
        )

        channel_handle = _extract_channel_handle(channel_url)
        if not channel_handle:
            return None, None, _build_meta(
                source_type=source_type,
                message="Could not extract channel handle or ID from URL",
            )

        videos = _search_channel_videos(
            channel_url,
            channel_handle,
            title_keyword,
            duration_cap,
            timeout_seconds=25,
        )
        
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
                if not output.exists() or output.stat().st_size <= 0:
                    continue

                audio_valid, audio_msg = _validate_audio(str(output))
                if not audio_valid:
                    print(f"Audio validation failed for {video_id}: {audio_msg}")
                    if output.exists():
                        output.unlink()
                    continue

                _append_downloaded_id(downloaded_file, video_id)
                print(f"Downloaded: {title} -> {output}")
                return str(output), title, _build_meta(
                    video_id=video_id,
                    source_type=source_type,
                    duplicate=False,
                    message="Video downloaded successfully.",
                )
            except Exception as exc:
                print(f"[DOWNLOAD] Failed for {video_id}: {exc}")
                if output.exists():
                    output.unlink()
                continue

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
