#!/bin/bash

echo "================================"
echo "Auto Quran Video Creator"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo ""
echo "Installing/updating dependencies..."
pip install -r requirements.txt

echo ""
echo "Creating required directories..."
mkdir -p assets
mkdir -p output

echo ""
echo "================================"
echo "Starting Flask server..."
echo "================================"
echo ""
echo "Open your browser and go to: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

export FLASK_APP=app.py
export FLASK_ENV=development
flask run
