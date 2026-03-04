import argparse

from scripts.main import create_and_post_quran_content


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Auto Quran orchestration pipeline.")
    parser.add_argument("--no-post", action="store_true", help="Build final video without posting to Instagram")
    parser.add_argument("--caption", default=None, help="Custom Instagram caption")
    parser.add_argument("--no-overlay", action="store_true", help="Skip transparent text overlay extraction")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    success = create_and_post_quran_content(
        post=not args.no_post,
        custom_caption=args.caption,
        use_text_overlay=not args.no_overlay,
    )
    if not success:
        raise SystemExit(1)
