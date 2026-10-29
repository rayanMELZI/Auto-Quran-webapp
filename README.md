# Auto Quran - Automated Quran Video Creator

A web application for creating beautiful Quran videos with nature backgrounds and text overlays, with automatic posting to Instagram.

## Features

- 🖼️ **Download Nature Images** - Fetch beautiful nature backgrounds from Unsplash
- 🎥 **Download Quran Videos** - Download Quran recitation videos from YouTube
- 📝 **Extract Text Overlay** - Create transparent text overlays from video
- 🎬 **Create Final Video** - Combine all elements into a final Instagram-ready video
- 📱 **Post to Instagram** - Automatically post the final video to Instagram
- ⚡ **Full Pipeline** - Run all steps automatically with one click
- 👀 **Live Previews** - Preview each step's output before proceeding

## Installation

1. Install Python dependencies:

```bash
pip install flask requests yt-dlp moviepy pillow instagrapi opencv-python python-dotenv imageio-ffmpeg
```

2. Create a `.env` file in the `logic` directory with your API credentials:

```
UNSPLASH_API_KEY=your_unsplash_api_key
INSTA_USERNAME=your_instagram_username
INSTA_PASSWORD=your_instagram_password
```

3. Create required directories (they will be created automatically if missing):

```bash
mkdir assets output
```

## Usage

### Web Application

1. Start the Flask server:

```bash
flask run
```

2. Open your browser and navigate to:

```
http://localhost:5000
```

3. Use the web interface to:
   - Run individual steps (download image, download video, etc.)
   - Preview each step's output
   - Run the full pipeline automatically
   - Post to Instagram with a custom caption

### Command Line (Individual Scripts)

Each script can be run independently from the command line:

#### Download Nature Image

```bash
python logic/scripts/download_image.py --output assets/nature_image.jpg
```

#### Download Quran Video

```bash
python logic/scripts/download_quran_video.py --output assets/quran_video.mp4
```

#### Extract Text Overlay

```bash
python logic/scripts/extract_text_from_video.py assets/quran_video.mp4 --output assets/quran_text_frame.mov
```

#### Create Final Video

```bash
python logic/scripts/create_final_video.py assets/nature_image.jpg assets/quran_video.mp4 --text-frame assets/quran_text_frame.mov --output output/final_output.mp4
```

#### Post to Instagram

```bash
python logic/scripts/post_to_instagram.py output/final_output.mp4 "Your caption here"
```

#### Run Full Pipeline

```bash
python logic/run_pipeline.py --no-post  # Generate video without posting
python logic/run_pipeline.py  # Generate and post to Instagram
```

## API Endpoints

- `GET /` - Web interface
- `POST /api/download-image` - Download nature image
- `POST /api/download-video` - Download Quran video
- `POST /api/extract-text` - Extract text overlay
- `POST /api/create-final` - Create final video
- `POST /api/post-instagram` - Post to Instagram
- `POST /api/run-full-pipeline` - Run complete pipeline
- `GET /api/preview/<media_type>` - Preview media (image/video/overlay/final)
- `GET /api/state` - Get current pipeline state
- `POST /api/reset` - Reset pipeline state

## Project Structure

```
Auto Quran/
├── app.py                      # Flask web application
├── logic/
│   ├── .env                    # API credentials (not in repo)
│   ├── run_pipeline.py         # Full pipeline orchestrator
│   └── scripts/
│       ├── download_image.py           # Download nature images
│       ├── download_quran_video.py     # Download Quran videos
│       ├── extract_text_from_video.py  # Extract text overlay
│       ├── create_final_video.py       # Create final composite
│       ├── post_to_instagram.py        # Post to Instagram
│       └── main.py                     # Pipeline orchestration
├── templates/
│   └── main.html               # Web interface
├── assets/                     # Downloaded media (auto-created)
└── output/                     # Final videos (auto-created)
```

## Configuration

### Unsplash API Key

Get your free API key from: https://unsplash.com/developers

### Instagram Credentials

Store your Instagram username and password in the `.env` file. The app uses session caching to minimize login requests.

### YouTube Channel

By default, the app downloads videos from `@Am9li9`. You can customize this in the web interface or script parameters.

## Notes

- Videos are processed at 1080x1920 (9:16 Instagram format)
- The app tracks downloaded videos to avoid duplicates
- Text overlay extraction uses FFmpeg colorkey filtering
- All scripts are designed to work independently or as part of a pipeline

## Troubleshooting

**Image download fails**: Check your Unsplash API key in `.env`

**Video download fails**: Ensure `yt-dlp` and `ffmpeg` are properly installed

**Instagram posting fails**: Verify credentials and check if Instagram requires verification

**Preview not showing**: Make sure the file was created successfully and check browser console for errors

## License

MIT License - Feel free to use and modify for your projects!
