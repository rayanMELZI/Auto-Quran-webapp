@echo off
echo ================================
echo Auto Quran Video Creator
echo ================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing/updating dependencies...
pip install -r requirements.txt

echo.
echo Creating required directories...
if not exist "assets\" mkdir assets
if not exist "output\" mkdir output

echo.
echo ================================
echo Starting Flask server...
echo ================================
echo.
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

set FLASK_APP=app.py
set FLASK_ENV=development
flask run
