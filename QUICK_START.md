# Quick Start Guide - Auto Quran Video Creator

## First Time Setup

### 1. Install Dependencies

Make sure you have Python 3.8+ installed, then install all required packages:

```bash
pip install -r requirements.txt
```

### 2. Configure API Credentials

1. Copy the example environment file:

```bash
cd logic
cp .env.example .env
```

2. Edit the `.env` file and add your credentials:
   - **Unsplash API Key**: Get from https://unsplash.com/developers (free)
   - **Instagram Username**: Your Instagram account username
   - **Instagram Password**: Your Instagram account password

Example `.env` file:

```
UNSPLASH_API_KEY=abc123xyz789yourkey
INSTA_USERNAME=your_username
INSTA_PASSWORD=your_password
```

### 3. Start the Application

#### Windows:

Double-click `start.bat` or run:

```bash
start.bat
```

#### Linux/Mac:

```bash
chmod +x start.sh
./start.sh
```

Or manually:

```bash
flask run
```

### 4. Open the Web Interface

Open your browser and go to:

```
http://localhost:5000
```

---

## Using the Web Interface

### Option A: Step-by-Step Mode

Use this when you want full control over each step:

1. **Download Image** (Step 1)
   - Click "Download Image" button
   - Wait for the nature background to download
   - Preview appears automatically

2. **Download Video** (Step 2)
   - Click "Download Video" button
   - Waits for a new Quran video from YouTube
   - Preview appears when ready

3. **Extract Text Overlay** (Step 3) - Optional
   - Only enabled after video downloads
   - Click "Extract Text" to create transparent overlay
   - Preview shows the text layer

4. **Create Final Video** (Step 4)
   - Only enabled after image and video are ready
   - Click "Create Final Video" to composite everything
   - Final preview appears (this may take 1-2 minutes)

5. **Post to Instagram**
   - Add custom caption or leave empty for default
   - Click "Share on Instagram"
   - Success notification appears when posted

### Option B: Full Pipeline Mode

Use this for automatic processing:

1. Click **"Run Full Pipeline"** button
2. Wait for all steps to complete automatically
3. Preview the final video
4. Add caption and post to Instagram

---

## Features Explained

### Individual Steps Panel (Left Side)

- Each step shows its current status (Pending/Processing/Completed/Error)
- Results can be previewed immediately
- Steps can be run multiple times
- Later steps automatically enable when dependencies are ready

### Quick Actions Panel (Right Top)

- **Run Full Pipeline**: Executes all steps automatically
- **Reset All**: Clears all progress and previews

### Instagram Post Panel (Right Middle)

- Custom caption textarea
- Auto-generates default caption if left empty
- Shows success/error messages

### Pipeline Status Panel (Right Bottom)

- Real-time status of all steps
- Shows which steps are ready
- Displays video title when available

---

## Tips & Tricks

### Custom Image Search

To use different image queries, you can modify the API call or use command line:

```bash
python logic/scripts/download_image.py --query "mountains sunset"
```

### Skip Text Overlay

If the Quran video doesn't have text or you want faster processing:

1. Skip step 3 (Extract Text Overlay)
2. Go directly to step 4 (Create Final Video)

### Reuse Previous Steps

- Downloaded image and video are cached
- You can skip re-downloading if files exist
- Click "Reset All" to start fresh

### View Generated Files

- Images: `assets/nature_image.jpg`
- Videos: `assets/quran_video.mp4`
- Text Overlay: `assets/quran_text_frame.mov`
- Final Video: `output/final_output.mp4`

### Test Without Posting

Run the full pipeline without posting:

```bash
python logic/run_pipeline.py --no-post
```

---

## Troubleshooting

### "Failed to download image"

- Check your Unsplash API key in `logic/.env`
- Verify internet connection
- Check API rate limits (50 requests/hour for free tier)

### "Failed to download video"

- YouTube may be rate limiting
- Try again later
- Check if the channel (@Am9li9) is still available

### "Failed to create final video"

- Ensure ffmpeg is installed (installed via imageio-ffmpeg)
- Check available disk space
- Verify input files exist in `assets/` folder

### "Failed to post to Instagram"

- Verify credentials in `logic/.env`
- Instagram may require verification (check email/SMS)
- Try deleting `instagram_session.json` and re-login
- Ensure the final video meets Instagram requirements (max 90 seconds)

### Preview not loading

- Check browser console (F12) for errors
- Ensure files were created successfully
- Try refresh preview button
- Check file permissions

### Port already in use

If port 5000 is already taken:

```bash
flask run --port 5001
```

---

## Advanced Usage

### Command Line Scripts

Each script can run independently:

```bash
# Download specific image
python logic/scripts/download_image.py --query "sunset beach" --output my_image.jpg

# Download with custom YouTube channel
python logic/scripts/download_quran_video.py --channel-url "https://youtube.com/@channel/videos"

# Extract with custom colorkey settings
python logic/scripts/extract_text_from_video.py video.mp4 --similarity 0.5

# Create final without overlay
python logic/scripts/create_final_video.py image.jpg video.mp4 --output final.mp4

# Post with custom caption
python logic/scripts/post_to_instagram.py video.mp4 "My custom caption #Quran"
```

### API Endpoints

Use the REST API directly:

```bash
# Download image
curl -X POST http://localhost:5000/api/download-image

# Get pipeline state
curl http://localhost:5000/api/state

# Reset pipeline
curl -X POST http://localhost:5000/api/reset
```

---

## Best Practices

1. **Test First**: Run with `--no-post` to verify video quality before posting
2. **Caption Strategy**: Customize captions for better engagement
3. **Schedule Posts**: Use cron/Task Scheduler to automate daily posts
4. **Backup Videos**: Keep copies of successful videos in a separate folder
5. **Monitor Logs**: Check console output for any warnings or errors
6. **API Limits**: Respect Unsplash and Instagram rate limits
7. **Quality Check**: Always preview before posting

---

## Automation

### Schedule Daily Posts (Windows Task Scheduler)

1. Create a batch file `daily_post.bat`:

```batch
cd "C:\path\to\Auto Quran"
python logic\run_pipeline.py
```

2. Open Task Scheduler
3. Create new task with daily trigger
4. Set action to run `daily_post.bat`

### Schedule Daily Posts (Linux/Mac Cron)

1. Edit crontab:

```bash
crontab -e
```

2. Add daily job (runs at 9 AM):

```
0 9 * * * cd /path/to/Auto\ Quran && python logic/run_pipeline.py
```

---

## Support

For issues or questions:

1. Check this guide first
2. Review README.md for technical details
3. Check GitHub issues
4. Ensure all dependencies are up to date

---

## License

MIT License - Free to use and modify!
