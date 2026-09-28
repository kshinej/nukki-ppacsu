"""
macOS DMG Disk Image Builder for LottieConverter.
Bundles dist/LottieConverter.app into LottieConverter.dmg.
"""

import os
import sys
import subprocess


def build_mac_dmg():
    print("==================================================")
    print(" Building macOS Disk Image (LottieConverter.dmg)")
    print("==================================================")

    app_path = "dist/LottieConverter.app"
    dmg_path = "dist/LottieConverter.dmg"

    if not os.path.exists(app_path):
        # If .app not built yet, run build_mac_app.py first
        print("LottieConverter.app not found. Building .app bundle first...")
        from build_mac_app import build_mac_app
        build_mac_app()

    if not os.path.exists(app_path):
        print(f"Error: {app_path} could not be built.")
        sys.exit(1)

    if sys.platform != 'darwin':
        print("Note: Native DMG creation requires macOS environment (hdiutil tool).")
        print("The build script 'build_mac_dmg.py' is ready to run on macOS!")
        return

    cmd = [
        "hdiutil", "create",
        "-volname", "LottieConverter",
        "-srcfolder", app_path,
        "-ov",
        "-format", "UDZO",
        dmg_path
    ]

    print(f"Creating {dmg_path} using hdiutil...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n==================================================")
        print(" SUCCESS: macOS DMG Disk Image Created!")
        print(f" Location: {dmg_path}")
        print("==================================================")
    else:
        print("\nFAILED: hdiutil DMG creation failed.")


if __name__ == "__main__":
    build_mac_dmg()
