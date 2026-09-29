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

    import shutil

    # 1. Install PyInstaller if missing
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # Clean previous build artifacts
    for p in ["build", "dist/LottieConverter.app", "dist/LottieConverter"]:
        if os.path.exists(p):
            print(f"Cleaning previous build artifact: {p}")
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)

    # Set PyInstaller config/cache dir within workspace to prevent permission issues on macOS
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".pyinstaller_cache"))
    os.makedirs(cache_dir, exist_ok=True)
    env = os.environ.copy()
    env["PYINSTALLER_CONFIG_DIR"] = cache_dir

    # 2. PyInstaller Command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name", "LottieConverter",
        "--osx-bundle-identifier", "com.lottieconverter.app",
        "--collect-all", "cv2",
        "--collect-all", "PIL",
        "--collect-all", "tkinterdnd2",
        "--add-data", f"config.py{os.path.pathsep}.",
        "gui.py"
    ]

    print("Running PyInstaller build command...")
    result = subprocess.run(cmd, env=env)


    if result.returncode == 0:
        # Remove quarantine attribute if present
        subprocess.run(["xattr", "-cr", "dist/LottieConverter.app"], stderr=subprocess.DEVNULL)
        print("\n==================================================")
        print(" SUCCESS: macOS Application Bundle Created!")
        print(" Location: dist/LottieConverter.app")
        print(" You can drag dist/LottieConverter.app to /Applications")
        print("==================================================")
    else:
        print("\nFAILED: PyInstaller build process encountered errors.")
        sys.exit(result.returncode)



if __name__ == "__main__":
    build_mac_app()
