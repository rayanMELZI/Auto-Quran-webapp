import argparse
import subprocess
from pathlib import Path
from typing import Optional

import imageio_ffmpeg


def extract_text_from_video(
    video_path: str,
    output_path: str = "assets/quran_text_frame.mov",
    colorkey_similarity: float = 0.3,
    colorkey_blend: float = 0.1,
) -> Optional[str]:
    print("Processing video to remove black background...")

    input_video = Path(video_path)
    if not input_video.exists():
        print(f"Input video not found: {input_video}")
        return None

    output_video = Path(output_path)
    output_video.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    video_filter = f"colorkey=black:{colorkey_similarity}:{colorkey_blend},format=rgba"

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(input_video),
        "-vf",
        video_filter,
        "-c:v",
        "qtrle",
        "-an",
        str(output_video),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Processed video saved with transparent background: {output_video}")
        return str(output_video)
    except subprocess.CalledProcessError as exc:
        print("FFmpeg failed while extracting transparent text layer.")
        print(exc.stderr)
        return None


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract transparent text layer from Quran video.")
    parser.add_argument("video_path", help="Input Quran video path")
    parser.add_argument("--output", default="assets/quran_text_frame.mov", help="Output transparent overlay path")
    parser.add_argument("--similarity", type=float, default=0.3, help="Colorkey similarity")
    parser.add_argument("--blend", type=float, default=0.1, help="Colorkey blend")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    result = extract_text_from_video(
        video_path=args.video_path,
        output_path=args.output,
        colorkey_similarity=args.similarity,
        colorkey_blend=args.blend,
    )
    if not result:
        raise SystemExit(1)
    print(result)