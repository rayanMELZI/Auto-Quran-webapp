import argparse
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
from moviepy.editor import CompositeVideoClip, ImageClip, VideoFileClip
from proglog import ProgressBarLogger


class _EncodingLogger(ProgressBarLogger):
    def __init__(self, progress_callback: Optional[Callable[[float, str], None]] = None):
        super().__init__()
        self._progress_callback = progress_callback

    def bars_callback(self, bar, attr, value, old_value=None):
        if not self._progress_callback:
            return

        if bar != "t" or attr != "index":
            return

        total = self.bars.get("t", {}).get("total")
        if not total:
            return

        percent = min(100.0, (float(value) / float(total)) * 100.0)
        self._progress_callback(percent, f"Encoding final video... {percent:.1f}%")


def _prepare_background(image_path: str, duration: float) -> ImageClip:
    background: Any = ImageClip(image_path)
    background = background.resize(height=1920)

    if background.w > 1080:
        x_center = background.w / 2
        background = background.crop(x1=x_center - 540, y1=0, x2=x_center + 540, y2=1920)
    elif background.w < 1080:
        background = background.resize(width=1080)
        if background.h > 1920:
            y_center = background.h / 2
            background = background.crop(x1=0, y1=y_center - 960, x2=1080, y2=y_center + 960)

    background = background.set_duration(duration)
    return background.fl_image(lambda frame: (np.array(frame) * 0.7).astype("uint8"))


def create_final_video(
    image_path: str,
    quran_video_path: str,
    text_frame_path: Optional[str] = None,
    output_path: str = "output/final_output.mp4",
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Optional[str]:
    print("Creating final video...")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    video_clip = None
    overlay_clip = None
    background_clip = None
    final_clip = None

    try:
        video_clip = VideoFileClip(quran_video_path)
        duration = video_clip.duration
        background_clip = _prepare_background(image_path, duration)

        clips = [background_clip]

        if text_frame_path and Path(text_frame_path).exists():
            overlay_clip = VideoFileClip(text_frame_path, has_mask=True).without_audio()
            overlay_clip = overlay_clip.resize(width=1000).set_position("center").set_duration(duration)
            clips.append(overlay_clip)

        final_clip = CompositeVideoClip(clips).set_audio(video_clip.audio)
        logger = _EncodingLogger(progress_callback=progress_callback)
        final_clip.write_videofile(
            str(output),
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="fast",
            threads=4,
            logger=logger,
        )

        if progress_callback:
            progress_callback(100.0, "Final video completed")

        print(f"Final video created: {output}")
        return str(output)
    except Exception as exc:
        print(f"Error creating final video: {exc}")
        return None
    finally:
        for clip in [overlay_clip, background_clip, final_clip, video_clip]:
            if clip is not None:
                clip.close()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create the final Quran Instagram video.")
    parser.add_argument("image_path", help="Background image path")
    parser.add_argument("quran_video_path", help="Original Quran video path")
    parser.add_argument("--text-frame", default=None, help="Transparent text overlay video path")
    parser.add_argument("--output", default="output/final_output.mp4", help="Final output path")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    result = create_final_video(
        image_path=args.image_path,
        quran_video_path=args.quran_video_path,
        text_frame_path=args.text_frame,
        output_path=args.output,
    )
    if not result:
        raise SystemExit(1)
    print(result)