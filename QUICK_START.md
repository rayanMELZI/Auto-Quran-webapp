# Auto Quran - Quick Start Guide

## 🚀 Super Quick Start (Docker)

1. **Setup**

   ```bash
   # Windows
   dev.bat setup

   # Linux/Mac
   chmod +x dev.sh
   ./dev.sh setup
   ```

2. **Edit credentials**
   - Open `backend/.env`
   - Add your Unsplash API key, Instagram username and password

3. **Start**

   ```bash
   # Windows
   dev.bat start

   # Linux/Mac
   ./dev.sh start
   ```

4. **Access**
   - Frontend: http://localhost
   - Backend: http://localhost:5000/api

## 📋 Common Commands

```bash
# View logs
dev.bat logs      # Windows
./dev.sh logs     # Linux/Mac

# Stop services
dev.bat stop      # Windows
./dev.sh stop     # Linux/Mac

# Restart services
dev.bat restart   # Windows
./dev.sh restart  # Linux/Mac
```

## ⚙️ Getting API Keys

### Unsplash API Key

1. Go to https://unsplash.com/developers
2. Register your application
3. Copy the Access Key
4. Add to `backend/.env` as `UNSPLASH_API_KEY`

### Instagram Credentials

1. Use your Instagram username and password
2. Disable two-factor authentication (or use app password)
3. Add to `backend/.env`:
   - `INSTA_USERNAME`
   - `INSTA_PASSWORD`

## 🎯 Usage Tips

- **Individual Steps**: Use for testing or customizing each step
- **Full Pipeline**: Automate everything with one click
- **Toggle Instagram**: Disable auto-posting if you want to preview first
- **Preview**: Each step shows a preview before proceeding

## 🐛 Troubleshooting

**Backend not connecting?**

```bash
docker-compose logs backend
```

**Port already in use?**

- Edit ports in `docker-compose.yml`
- Or stop conflicting services

**Instagram login failed?**

- Check credentials in `backend/.env`
- Disable 2FA temporarily
- Wait a few minutes and try again

## 📚 Full Documentation

See [README.md](README.md) for complete documentation.
