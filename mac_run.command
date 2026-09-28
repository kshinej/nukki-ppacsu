#!/bin/bash
# macOS Double-Click Launcher for Video-to-Lottie & GIF Converter
# Works on Apple Silicon (M1/M2/M3/M4) and Intel Macs

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================="
echo "  🎬 Video-to-Lottie & GIF Converter (macOS)"
echo "=================================================="

# Check Python 3 installation
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 could not be found. Please install Python 3.11+ on your Mac."
    echo "You can install it via Homebrew: 'brew install python' or from python.org"
    exit 1
fi

# Create virtualenv if not exists
if [ ! -d "venv" ]; then
    echo "[1/2] Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "[2/2] Installing required packages (opencv-python, numpy, pillow)..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "Starting GUI application..."
python3 gui.py
