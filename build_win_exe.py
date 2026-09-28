"""
Windows Standalone .exe Builder for LottieConverter.
Creates a single standalone executable dist/LottieConverter.exe.
"""

import os
import sys
import subprocess


def build_win_exe():
    print("==================================================")
    print(" Building Windows Executable (LottieConverter.exe)")
    print("==================================================")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "LottieConverter",
        "gui.py"
    ]

    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\n==================================================")
        print(" SUCCESS: Windows Executable Created!")
        print(" Location: dist/LottieConverter.exe")
        print("==================================================")
    else:
        print("\nFAILED: PyInstaller build failed.")


if __name__ == "__main__":
    build_win_exe()
