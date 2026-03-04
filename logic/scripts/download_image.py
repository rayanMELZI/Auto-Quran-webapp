import argparse
import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv


def download_nature_image(
    output_path: str = "assets/nature_image.jpg",
    query: str = "nature landscape",
    fallback_path: str = "assets/default_nature.jpg",
    unsplash_api_key: Optional[str] = None,
) -> Optional[str]:
    print("Downloading nature image...")

    load_dotenv()
    api_key = unsplash_api_key or os.getenv("UNSPLASH_API_KEY")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if not api_key:
        print("UNSPLASH_API_KEY is missing. Using fallback image if available.")
        return fallback_path if Path(fallback_path).exists() else None

    url = "https://api.unsplash.com/photos/random"
    params = {
        "query": query,
        "orientation": "portrait",
        "client_id": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        image_data = response.json()
        image_url = image_data["urls"]["full"]
        image_author = image_data["user"].get("name", "Unknown")

        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()

        with open(output, "wb") as handler:
            handler.write(img_response.content)

        print(f"Image downloaded successfully from {image_author} -> {output}")
        return str(output)
    except Exception as exc:
        print(f"Error downloading image: {exc}")
        if Path(fallback_path).exists():
            print(f"Using fallback image: {fallback_path}")
            return fallback_path
        return None


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download a nature image from Unsplash.")
    parser.add_argument("--output", default="assets/nature_image.jpg", help="Output image path")
    parser.add_argument("--query", default="nature landscape", help="Search query")
    parser.add_argument("--fallback", default="assets/default_nature.jpg", help="Fallback image path")
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    result = download_nature_image(
        output_path=args.output,
        query=args.query,
        fallback_path=args.fallback,
    )
    if not result:
        raise SystemExit(1)
    print(result)