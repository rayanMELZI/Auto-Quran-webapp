# import argparse
# import logging
# import os
# import time
# from pathlib import Path
# from typing import Any, Dict, Optional

# from dotenv import load_dotenv
# from instagrapi import Client
# from instagrapi.exceptions import (
#     BadCredentials,
#     ChallengeRequired,
#     ClientConnectionError,
#     ClientError,
#     ClientLoginRequired,
#     ClientThrottledError,
#     FeedbackRequired,
#     LoginRequired,
#     PleaseWaitFewMinutes,
#     ProxyAddressIsBlocked,
#     RateLimitError,
#     ReloginAttemptExceeded,
#     SentryBlock,
#     TwoFactorRequired,
# )

# logger = logging.getLogger(__name__)

# # Repo root: logic/scripts -> parents[2]
# _PROJECT_ROOT = Path(__file__).resolve().parents[2]


# def _ensure_env_loaded() -> None:
#     load_dotenv(_PROJECT_ROOT / ".env", override=False)
#     load_dotenv(override=False)


# def _resolve_session_path(session_file: Optional[str]) -> Path:
#     raw = (
#         session_file
#         or os.getenv("INSTAGRAM_SESSION_FILE")
#         or os.getenv("INSTA_SESSION_FILE")
#         or "assets/instagram_session.json"
#     )
#     p = Path(raw)
#     if not p.is_absolute():
#         p = (_PROJECT_ROOT / p).resolve()
#     p.parent.mkdir(parents=True, exist_ok=True)
#     return p


# def _get_credentials() -> tuple[Optional[str], Optional[str]]:
#     username = (
#         os.getenv("INSTA_USERNAME")
#         or os.getenv("INSTAGRAM_USERNAME")
#         or os.getenv("IG_USERNAME")
#     )
#     password = (
#         os.getenv("INSTA_PASSWORD")
#         or os.getenv("INSTAGRAM_PASSWORD")
#         or os.getenv("IG_PASSWORD")
#     )
#     return (username.strip() if username else None, password if password else None)


# def _mask_username(u: str) -> str:
#     if len(u) <= 2:
#         return "***"
#     return f"{u[:2]}…{u[-1]}"


# def _classify_instagram_error(exc: BaseException) -> tuple[str, str]:
#     """Return (error_category, user_safe_message)."""
#     msg = str(exc).strip()
#     lower = msg.lower()

#     if isinstance(
#         exc,
#         (
#             BadCredentials,
#             TwoFactorRequired,
#             ChallengeRequired,
#             LoginRequired,
#             ClientLoginRequired,
#         ),
#     ):
#         return "auth", "Instagram login failed or session expired. Re-save session or check credentials."

#     if isinstance(exc, (ClientThrottledError, PleaseWaitFewMinutes, RateLimitError)):
#         return "rate_limit", "Instagram rate-limited this connection. Wait several minutes and try again."

#     if isinstance(exc, (FeedbackRequired, SentryBlock, ReloginAttemptExceeded)):
#         return "blocked", (
#             "Instagram blocked this login (feedback / sentry). Often IP-related: try another network, "
#             "residential proxy, or log in from the official app once from the same IP."
#         )

#     if isinstance(exc, ProxyAddressIsBlocked):
#         return "proxy", "The configured proxy IP is blocked by Instagram. Use a different residential proxy."

#     if isinstance(exc, ClientConnectionError):
#         return "network", "Could not reach Instagram (network). Check firewall, DNS, and proxy settings."

#     if isinstance(exc, ClientError):
#         if "blacklist" in lower or "facebook" in lower and "linked" in lower:
#             return "ip_block", (
#                 "Instagram rejected this IP (often datacenter/VPN). Try a residential IP, mobile hotspot, "
#                 "or a trusted proxy; reuse a session created on a clean IP."
#             )
#         if "checkpoint" in lower or "challenge" in lower:
#             return "challenge", "Instagram requires verification in the app or browser before API login works."
#         return "client_error", msg[:280] if msg else "Instagram API error."

#     return "unknown", msg[:280] if msg else "Unknown error posting to Instagram."


# def post_to_instagram(
#     video_path: str,
#     caption: str,
#     thumbnail_path: str = "assets/nature_image.jpg",
#     session_file: Optional[str] = None,
# ) -> Dict[str, Any]:
#     """
#     Upload a reel to Instagram using instagrapi.

#     Returns a dict: success (bool), message (user-facing), error_category (optional),
#     detail (optional, for server logs only).
#     """
#     _ensure_env_loaded()

#     result: Dict[str, Any] = {
#         "success": False,
#         "message": "",
#         "error_category": None,
#         "detail": None,
#     }

#     username, password = _get_credentials()
#     session_path = _resolve_session_path(session_file)

#     if not username or not password:
#         result["message"] = (
#             "Instagram credentials missing. Set INSTA_USERNAME and INSTA_PASSWORD in .env "
#             "(or INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD)."
#         )
#         result["error_category"] = "config"
#         logger.error("Instagram: missing INSTA_USERNAME / INSTA_PASSWORD in environment")
#         return result

#     logger.info(
#         "Instagram: starting upload for user=%s session_file=%s video=%s",
#         _mask_username(username),
#         session_path,
#         video_path,
#     )

#     vid_p = Path(video_path)
#     if not vid_p.is_absolute():
#         vid_p = _PROJECT_ROOT / vid_p
#     if not vid_p.exists():
#         result["message"] = f"Video file not found: {vid_p}"
#         result["error_category"] = "validation"
#         logger.error("Instagram: video missing at %s", video_path)
#         return result

#     thumb_p = Path(thumbnail_path)
#     if not thumb_p.is_absolute():
#         thumb_p = _PROJECT_ROOT / thumb_p
#     thumb = str(thumb_p) if thumb_p.exists() else None
#     if thumb is None:
#         logger.warning("Instagram: thumbnail not found at %s, uploading without custom thumb", thumbnail_path)

#     proxy = (
#         os.getenv("INSTAGRAM_PROXY")
#         or os.getenv("INSTA_PROXY")
#         or os.getenv("HTTPS_PROXY")
#         or os.getenv("HTTP_PROXY")
#     )

#     pre_delay = float(os.getenv("INSTAGRAM_LOGIN_DELAY_SECONDS", "0") or "0")
#     if pre_delay > 0:
#         logger.info("Instagram: sleeping %.1fs before login (INSTAGRAM_LOGIN_DELAY_SECONDS)", pre_delay)
#         time.sleep(pre_delay)

#     try:
#         cl = Client()
#         if proxy:
#             try:
#                 cl.set_proxy(proxy)
#                 logger.info("Instagram: using proxy from environment")
#             except Exception as pe:
#                 logger.warning("Instagram: set_proxy failed: %s", pe)

#         if session_path.exists():
#             try:
#                 cl.load_settings(str(session_path))
#                 cl.get_timeline_feed()
#                 logger.info("Instagram: session OK at %s", session_path)
#             except LoginRequired:
#                 logger.info("Instagram: session expired, full login")
#                 cl.login(username, password)
#                 cl.dump_settings(str(session_path))
#                 logger.info("Instagram: new session saved to %s", session_path)
#         else:
#             logger.info("Instagram: no session file, logging in")
#             cl.login(username, password)
#             cl.dump_settings(str(session_path))
#             logger.info("Instagram: session saved to %s", session_path)

#         logger.info("Instagram: uploading clip…")
#         media = cl.clip_upload(
#             str(vid_p),
#             caption=caption,
#             thumbnail=thumb,
#             extra_data={
#                 "custom_accessibility_caption": "Quran Verse",
#                 "like_and_view_counts_disabled": False,
#                 "disable_comments": False,
#             },
#         )

#         result["success"] = True
#         result["message"] = f"Posted successfully (media id {media.id})."
#         logger.info("Instagram: upload OK media_id=%s", media.id)
#         return result

#     except Exception as exc:
#         category, user_msg = _classify_instagram_error(exc)
#         result["message"] = user_msg
#         result["error_category"] = category
#         result["detail"] = repr(exc)
#         logger.exception(
#             "Instagram: upload failed category=%s user_message=%s",
#             category,
#             user_msg,
#         )
#         return result


# def _build_arg_parser() -> argparse.ArgumentParser:
#     parser = argparse.ArgumentParser(description="Upload a video reel to Instagram.")
#     parser.add_argument("video_path", help="Path to the final video")
#     parser.add_argument("caption", help="Caption text")
#     parser.add_argument("--thumbnail", default="assets/nature_image.jpg", help="Thumbnail image path")
#     parser.add_argument("--session-file", default=None, help="Path to session json (default: env or assets/)")
#     return parser


# if __name__ == "__main__":
#     args = _build_arg_parser().parse_args()
#     out = post_to_instagram(
#         # video_path=args.video_path,
#         video_path="/assets/quran_video.mp4",
#         caption=args.caption,
#         thumbnail_path=args.thumbnail,
#         session_file=args.session_file,
#     )
#     print(out.get("message", out))
#     if not out.get("success"):
#         raise SystemExit(1)



"""
logic/scripts/post_to_instagram.py

Uploads a video reel to Instagram using instagrapi.
Returns a rich dict so callers get structured error info,
not just a boolean, and can surface specific advice to the user.
"""

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import (
    BadCredentials,
    ChallengeRequired,
    ClientConnectionError,
    ClientError,
    ClientLoginRequired,
    ClientThrottledError,
    FeedbackRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    ProxyAddressIsBlocked,
    RateLimitError,
    ReloginAttemptExceeded,
    SentryBlock,
    TwoFactorRequired,
)

logger = logging.getLogger(__name__)

# Project root is 2 levels above this file:
#   logic/scripts/post_to_instagram.py  →  parents[0] = logic/scripts/
#                                        →  parents[1] = logic/
#                                        →  parents[2] = project root  ✓
# This is used to resolve relative paths (assets/, output/) correctly
# regardless of which directory the caller launched Python from.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ── Internal helpers ───────────────────────────────────────────────────────────

def _ensure_env_loaded() -> None:
    """Load .env from project root, then current directory (for local dev)."""
    load_dotenv(_PROJECT_ROOT / ".env", override=False)
    load_dotenv(override=False)


def _resolve_session_path(session_file: Optional[str]) -> Path:
    """
    Resolve the Instagram session file path.

    Priority:
    1. Explicit argument (passed from Flask route via config)
    2. INSTAGRAM_SESSION_FILE env var
    3. Default: assets/instagram_session.json (relative to project root)

    The resolved path is always absolute so it works regardless of cwd.
    """
    raw = (
        session_file
        or os.getenv("INSTAGRAM_SESSION_FILE")
        or os.getenv("INSTA_SESSION_FILE")
        or "assets/instagram_session.json"
    )
    p = Path(raw)
    if not p.is_absolute():
        p = (_PROJECT_ROOT / p).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _get_credentials() -> tuple[Optional[str], Optional[str]]:
    """Read credentials from environment. Accepts multiple variable name conventions."""
    username = (
        os.getenv("INSTA_USERNAME")
        or os.getenv("INSTAGRAM_USERNAME")
        or os.getenv("IG_USERNAME")
    )
    password = (
        os.getenv("INSTA_PASSWORD")
        or os.getenv("INSTAGRAM_PASSWORD")
        or os.getenv("IG_PASSWORD")
    )
    return (username.strip() if username else None, password if password else None)


def _mask_username(u: str) -> str:
    """Return a partially masked username for safe logging."""
    if len(u) <= 2:
        return "***"
    return f"{u[:2]}…{u[-1]}"


def _classify_instagram_error(exc: BaseException) -> tuple[str, str]:
    """
    Map an exception to (error_category, user_safe_message).

    error_category is a short machine-readable string the frontend can
    use to decide what help text to show.
    """
    msg   = str(exc).strip()
    lower = msg.lower()

    if isinstance(exc, (BadCredentials, TwoFactorRequired, ChallengeRequired,
                        LoginRequired, ClientLoginRequired)):
        return "auth", (
            "Instagram login failed or session expired. "
            "Delete assets/instagram_session.json and let the app log in again."
        )

    if isinstance(exc, (ClientThrottledError, PleaseWaitFewMinutes, RateLimitError)):
        return "rate_limit", "Instagram rate-limited this connection. Wait a few minutes and try again."

    if isinstance(exc, (FeedbackRequired, SentryBlock, ReloginAttemptExceeded)):
        return "blocked", (
            "Instagram blocked this login (feedback/sentry block). "
            "Often IP-related: log in from the official app on the same IP first, "
            "or use a residential proxy."
        )

    if isinstance(exc, ProxyAddressIsBlocked):
        return "proxy", "The proxy IP is blocked by Instagram. Use a different residential proxy."

    if isinstance(exc, ClientConnectionError):
        return "network", "Could not reach Instagram. Check your VM's internet access and firewall."

    if isinstance(exc, ClientError):
        if "blacklist" in lower or ("facebook" in lower and "linked" in lower):
            return "ip_block", (
                "Instagram rejected this IP (often datacenter/VPN). "
                "Try posting from a mobile hotspot or residential proxy."
            )
        if "checkpoint" in lower or "challenge" in lower:
            return "challenge", (
                "Instagram requires human verification. "
                "Open the official app and complete any pending challenge, then retry."
            )
        return "client_error", msg[:280] if msg else "Instagram API error."

    return "unknown", msg[:280] if msg else "Unknown error posting to Instagram."


# ── Public API ─────────────────────────────────────────────────────────────────

def post_to_instagram(
    video_path: str,
    caption: str,
    thumbnail_path: str = "assets/nature_image.jpg",
    session_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Upload a reel to Instagram.

    Returns a dict with these keys:
        success        (bool)  — True = uploaded OK
        message        (str)   — Human-readable outcome, safe to show in the UI
        error_category (str|None) — Machine-readable error type for the frontend
        detail         (str|None) — Full exception repr for server logs; don't show to users

    WHY A DICT INSTEAD OF BOOL?
    A bool can only say "it worked" or "it failed".
    A dict lets the UI tell the user WHY it failed and what to do about it
    (e.g. "your session expired" vs "Instagram blocked your IP" are very
    different problems that need different solutions).
    """
    _ensure_env_loaded()

    result: Dict[str, Any] = {
        "success":        False,
        "message":        "",
        "error_category": None,
        "detail":         None,
    }

    # ── Credentials check ──────────────────────────────────────────────────────
    username, password = _get_credentials()
    session_path       = _resolve_session_path(session_file)

    if not username or not password:
        result["message"]        = (
            "Instagram credentials missing. "
            "Set INSTA_USERNAME and INSTA_PASSWORD in your .env file."
        )
        result["error_category"] = "config"
        logger.error("Instagram: missing credentials in environment")
        return result

    logger.info(
        "Instagram: upload requested user=%s session=%s video=%s",
        _mask_username(username), session_path, video_path,
    )

    # ── Validate file paths ────────────────────────────────────────────────────
    vid_p = Path(video_path)
    if not vid_p.is_absolute():
        vid_p = _PROJECT_ROOT / vid_p

    if not vid_p.exists():
        result["message"]        = f"Video file not found: {vid_p}"
        result["error_category"] = "validation"
        logger.error("Instagram: video missing at %s", vid_p)
        return result

    thumb_p = Path(thumbnail_path)
    if not thumb_p.is_absolute():
        thumb_p = _PROJECT_ROOT / thumb_p
    thumb = str(thumb_p) if thumb_p.exists() else None
    if thumb is None:
        logger.warning("Instagram: thumbnail not found at %s — uploading without thumbnail", thumbnail_path)

    # ── Optional proxy ─────────────────────────────────────────────────────────
    proxy = (
        os.getenv("INSTAGRAM_PROXY")
        or os.getenv("INSTA_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
    )

    # ── Optional pre-login delay (helps with rate limiting on fresh sessions) ──
    pre_delay = float(os.getenv("INSTAGRAM_LOGIN_DELAY_SECONDS", "0") or "0")
    if pre_delay > 0:
        logger.info("Instagram: sleeping %.1fs before login", pre_delay)
        time.sleep(pre_delay)

    # ── Login and upload ───────────────────────────────────────────────────────
    try:
        cl = Client()

        if proxy:
            try:
                cl.set_proxy(proxy)
                logger.info("Instagram: proxy configured")
            except Exception as proxy_exc:
                logger.warning("Instagram: set_proxy failed: %s", proxy_exc)

        # Session file exists → try to reuse it (avoids login challenge)
        if session_path.exists():
            try:
                cl.load_settings(str(session_path))
                cl.get_timeline_feed()   # lightweight auth check
                logger.info("Instagram: existing session is valid")
            except LoginRequired:
                # Session expired — do a full login and save a fresh session
                logger.info("Instagram: session expired, performing full login")
                cl.login(username, password)
                cl.dump_settings(str(session_path))
                logger.info("Instagram: fresh session saved to %s", session_path)
        else:
            # First run — log in and save session for next time
            logger.info("Instagram: no session file found, logging in fresh")
            cl.login(username, password)
            cl.dump_settings(str(session_path))
            logger.info("Instagram: session saved to %s", session_path)

        logger.info("Instagram: starting clip upload…")
        media = cl.clip_upload(
            path=vid_p,
            caption=caption,
            thumbnail=thumb,
            extra_data={
                "custom_accessibility_caption": "Quran Verse",
                "like_and_view_counts_disabled": "0",
                "disable_comments": "0",
            },
        )

        result["success"] = True
        result["message"] = f"Posted successfully (media id {media.id})."
        logger.info("Instagram: upload OK media_id=%s", media.id)
        return result

    except Exception as exc:
        category, user_msg      = _classify_instagram_error(exc)
        result["message"]        = user_msg
        result["error_category"] = category
        result["detail"]         = repr(exc)
        logger.exception(
            "Instagram: upload failed category=%s message=%s", category, user_msg
        )
        return result


# ── CLI entry point ────────────────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload a video reel to Instagram.")
    parser.add_argument("video_path", help="Path to the final video")
    parser.add_argument("caption",    help="Caption text")
    parser.add_argument("--thumbnail",    default="assets/nature_image.jpg")
    parser.add_argument("--session-file", default=None,
                        help="Session file path (default: env var or assets/)")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    out  = post_to_instagram(
        video_path=args.video_path,   # ← was accidentally hardcoded; fixed
        caption=args.caption,
        thumbnail_path=args.thumbnail,
        session_file=args.session_file,
    )
    print(out.get("message", out))
    if not out.get("success"):
        raise SystemExit(1)
