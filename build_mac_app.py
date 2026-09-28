"""
macOS .app Bundle Builder for LottieConverter.
Packages gui.py into a native macOS Application bundle (dist/LottieConverter.app)
using PyInstaller.
"""

import os
import sys
import subprocess


def build_mac_app():
    print("==================================================")
    print(" Building macOS Application Bundle (LottieConverter.app)")
    print("==================================================")

    # 1. Install PyInstaller if missing
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # 2. PyInstaller Command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "LottieConverter",
        "--add-data", f"config.py{os.path.pathsep}.",
        "gui.py"
    ]

    print("Running PyInstaller build command...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n==================================================")
        print(" SUCCESS: macOS Application Bundle Created!")
        print(" Location: dist/LottieConverter.app")
        print(" You can drag dist/LottieConverter.app to /Applications")
        print("==================================================")
    else:
        print("\nFAILED: PyInstaller build process encountered errors.")


if __name__ == "__main__":
    build_mac_app()
