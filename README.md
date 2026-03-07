# Auto Quran - Automated Quran Video Creator

A production-ready web application for creating beautiful Quran videos with nature backgrounds and text overlays, with automatic posting to Instagram.

## 🎯 Features

- **📷 Download Nature Images** - Fetch beautiful nature backgrounds from Unsplash
- **🎥 Download Quran Videos** - Download Quran recitation videos from YouTube
- **📝 Extract Text Overlay** - Create transparent text overlays from videos
- **🎬 Create Final Video** - Combine all elements into Instagram-ready videos
- **📱 Post to Instagram** - Automatically post videos to Instagram
- **⚡ Full Pipeline** - Run all steps automatically with one click
- **👀 Live Previews** - Preview each step's output before proceeding
- **🐳 Docker Support** - Fully containerized with Docker Compose

## 🏗️ Project Structure

```
Auto Quran/
├── backend/                 # Flask API backend
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration management
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Backend Docker image
│   └── .env.example        # Environment variables template
│
├── frontend/               # Static frontend
│   ├── index.html          # Main HTML file
│   ├── css/
│   │   └── style.css       # Styles
│   ├── js/
│   │   ├── config.js       # Frontend configuration
│   │   ├── api.js          # API client
│   │   └── app.js          # Application logic
│   ├── nginx.conf          # Nginx configuration
│   └── Dockerfile          # Frontend Docker image
│
├── logic/                  # Video processing logic
│   ├── run_pipeline.py     # Pipeline orchestration
│   └── scripts/            # Individual processing scripts
│       ├── download_image.py
│       ├── download_quran_video.py
│       ├── extract_text_from_video.py
│       ├── create_final_video.py
│       └── post_to_instagram.py
│
├── docker-compose.yml      # Development compose file
├── docker-compose.prod.yml # Production compose file
└── README.md              # This file
```

## 🚀 Quick Start with Docker

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

### Development Setup

1. **Clone the repository**

   ```bash
   cd "Auto Quran"
   ```

2. **Create environment file**

   ```bash
   cp backend/.env.example backend/.env
   ```

3. **Edit `.env` file with your credentials**

   ```bash
   # backend/.env
   UNSPLASH_API_KEY=your_unsplash_api_key
   INSTA_USERNAME=your_instagram_username
   INSTA_PASSWORD=your_instagram_password
   SECRET_KEY=your_secret_key
   ```

4. **Create data directory**

   ```bash
   mkdir -p data/assets data/output
   ```

5. **Start the application**

   ```bash
   docker-compose up -d
   ```

6. **Access the application**
   - Frontend: http://localhost
   - Backend API: http://localhost:5000/api

7. **View logs**

   ```bash
   docker-compose logs -f
   ```

8. **Stop the application**
   ```bash
   docker-compose down
   ```

### Production Deployment

For production, use the production compose file:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

The production configuration includes:

- Optimized logging
- Security hardening
- Named volumes for persistence
- Health checks
- Automatic restarts

## 💻 Manual Installation (without Docker)

### Backend Setup

1. **Install Python 3.11+**

2. **Create virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Install system dependencies**
   - FFmpeg: Required for video processing

     ```bash
     # Ubuntu/Debian
     sudo apt-get install ffmpeg

     # macOS
     brew install ffmpeg

     # Windows
     # Download from https://ffmpeg.org/download.html
     ```

5. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

6. **Run the backend**
   ```bash
   python app.py
   # Or with gunicorn:
   gunicorn --bind 0.0.0.0:5000 --workers 2 app:app
   ```

### Frontend Setup

For development, you can serve the frontend with any static file server:

```bash
cd frontend
python -m http.server 8080
# Or use Node.js http-server:
# npx http-server -p 8080
```

For production, use Nginx or another web server to serve the static files and proxy API requests to the backend.

## 📖 Usage

### Web Interface

1. Open the web application in your browser
2. Use individual steps or run the full pipeline:

   **Individual Steps:**
   - Step 1: Download a nature image from Unsplash
   - Step 2: Download a Quran recitation video from YouTube
   - Step 3: Extract text overlay from the video
   - Step 4: Create the final composite video
   - Step 5: Post to Instagram

   **Full Pipeline:**
   - Toggle "Post to Instagram" on/off
   - Click "Run Full Pipeline" to execute all steps automatically

### API Endpoints

The backend exposes a RESTful API:

- `GET /api/health` - Health check
- `GET /api/settings` - Get settings
- `POST /api/settings` - Update settings
- `POST /api/download-image` - Download nature image
- `POST /api/download-video` - Download Quran video
- `POST /api/extract-text` - Extract text overlay
- `POST /api/create-final-video` - Create final video
- `POST /api/post-to-instagram` - Post to Instagram
- `GET /api/progress` - Get current progress
- `GET /api/pipeline/state` - Get pipeline state
- `POST /api/pipeline/stop` - Stop current operation

### Command Line

Run the pipeline from the command line:

```bash
cd backend
python ../logic/run_pipeline.py
```

Options:

- `--no-post` - Build video without posting to Instagram
- `--caption "Your caption"` - Custom Instagram caption
- `--no-overlay` - Skip text overlay extraction

## 🔧 Configuration

### Environment Variables

Backend environment variables (backend/.env):

```env
# API Keys
UNSPLASH_API_KEY=your_key
INSTA_USERNAME=your_username
INSTA_PASSWORD=your_password

# Flask
SECRET_KEY=your_secret_key
FLASK_ENV=production
PORT=5000

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Application Settings

Settings can be configured via the web interface or by editing `assets/settings.json`:

```json
{
  "default_channel_url": "https://www.youtube.com/@YourChannel/videos",
  "default_keyword": "سورة",
  "default_caption": "Your default caption",
  "cronjob_enabled": false,
  "cronjob_time": "09:00"
}
```

## 🐳 Docker Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build

# Scale workers (backend only)
docker-compose up -d --scale backend=2
```

## 🔒 Security Notes

- Never commit `.env` files to version control
- Use strong SECRET_KEY in production
- Keep Instagram credentials secure
- Use HTTPS in production
- Regularly update dependencies
- Review and adjust CORS_ORIGINS for your domain

## 📝 Troubleshooting

### Docker Issues

**Cannot connect to backend:**

- Check if services are running: `docker-compose ps`
- View logs: `docker-compose logs backend`
- Restart services: `docker-compose restart`

**Port already in use:**

- Change ports in docker-compose.yml
- Stop conflicting services

### Instagram Issues

**Login failed:**

- Verify credentials in .env
- Check if 2FA is disabled
- Try generating an app-specific password

**Video upload failed:**

- Ensure video meets Instagram requirements (max 60s, specific formats)
- Check internet connection
- Review Instagram API limits

### Video Processing Issues

**FFmpeg errors:**

- Ensure FFmpeg is installed
- Check video format compatibility
- Review error logs

## 📄 License

This project is provided as-is for educational and personal use.

## 🙏 Acknowledgments

- Unsplash API for beautiful images
- yt-dlp for video downloads
- MoviePy for video processing
- Instagrapi for Instagram integration
- Flask for the backend API
- Nginx for serving the frontend

## 📧 Support

For issues and questions, please check the logs and troubleshooting section first.
