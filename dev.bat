@echo off
REM Auto Quran - Development Helper Script for Windows

setlocal enabledelayedexpansion

if "%1"=="" goto help
if "%1"=="setup" goto setup
if "%1"=="start" goto start
if "%1"=="start-prod" goto start_prod
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="logs" goto logs
if "%1"=="build" goto build
if "%1"=="clean" goto clean
if "%1"=="status" goto status
if "%1"=="help" goto help
goto help

:setup
echo [INFO] Setting up Auto Quran...
if not exist "backend\.env" (
    echo [WARN] .env file not found. Creating from template...
    copy backend\.env.example backend\.env
    echo [WARN] Please edit backend\.env with your credentials before starting!
) else (
    echo [INFO] .env file found
)
if not exist "data" mkdir data
if not exist "data\assets" mkdir data\assets
if not exist "data\output" mkdir data\output
echo [INFO] Setup complete! Edit backend\.env then run: dev.bat start
goto end

:start
echo [INFO] Starting Auto Quran services...
docker-compose up -d
echo [INFO] Services started
echo [INFO] Frontend: http://localhost
echo [INFO] Backend API: http://localhost:5000/api
echo.
echo [INFO] View logs: dev.bat logs
goto end

:start_prod
echo [INFO] Starting Auto Quran in production mode...
docker-compose -f docker-compose.prod.yml up -d
echo [INFO] Production services started
goto end

:stop
echo [INFO] Stopping Auto Quran services...
docker-compose down
echo [INFO] Services stopped
goto end

:restart
echo [INFO] Restarting Auto Quran services...
docker-compose restart
echo [INFO] Services restarted
goto end

:logs
docker-compose logs -f
goto end

:build
echo [INFO] Building Docker images...
docker-compose build
echo [INFO] Images built
goto end

:clean
set /p confirm="This will remove all containers and volumes. Continue? (y/N): "
if /i "%confirm%"=="y" (
    echo [INFO] Cleaning up...
    docker-compose down -v
    echo [INFO] Cleanup complete
) else (
    echo [INFO] Cleanup cancelled
)
goto end

:status
echo [INFO] Auto Quran Status:
docker-compose ps
goto end

:help
echo Auto Quran - Development Helper Script
echo.
echo Usage: dev.bat [command]
echo.
echo Commands:
echo     setup       - Initial setup (create .env and directories)
echo     start       - Start services in development mode
echo     start-prod  - Start services in production mode
echo     stop        - Stop all services
echo     restart     - Restart all services
echo     logs        - View logs (follow mode)
echo     build       - Build Docker images
echo     clean       - Remove containers and volumes
echo     status      - Show service status
echo     help        - Show this help message
echo.
echo Examples:
echo     dev.bat setup          # First time setup
echo     dev.bat start          # Start development
echo     dev.bat logs           # View logs
echo     dev.bat stop           # Stop services
echo.
goto end

:end
endlocal
