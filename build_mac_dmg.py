"""
macOS DMG Disk Image Builder for LottieConverter.
Bundles dist/LottieConverter.app into LottieConverter.dmg.
"""

import os
import sys
import subprocess
import shutil


def build_mac_dmg(force_rebuild=True):
    print("==================================================")
    print(" Building macOS Disk Image (LottieConverter.dmg)")
    print("==================================================")

    if sys.platform != 'darwin':
        print("Error: Native DMG creation requires macOS environment (hdiutil tool).")
        sys.exit(1)

    app_path = "dist/LottieConverter.app"
    dmg_path = "dist/LottieConverter.dmg"
    staging_dir = "dist/dmg_staging"

    # Always rebuild .app bundle to ensure latest dependencies and code are included
    if force_rebuild or not os.path.exists(app_path):
        print("Building fresh .app bundle...")
        from build_mac_app import build_mac_app
        build_mac_app()

    if not os.path.exists(app_path):
        print(f"Error: {app_path} could not be built.")
        sys.exit(1)

    # Prepare DMG staging directory
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir, exist_ok=True)

    print("Copying LottieConverter.app to staging directory...")
    # Use ditto on macOS to preserve permissions, symlinks, and resource forks
    subprocess.run(["ditto", app_path, os.path.join(staging_dir, "LottieConverter.app")], check=True)

    # Create /Applications symlink for easy drag-and-drop installation
    apps_link = os.path.join(staging_dir, "Applications")
    if not os.path.exists(apps_link):
        os.symlink("/Applications", apps_link)

    # Remove existing DMG if present
    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    cmd = [
        "hdiutil", "create",
        "-volname", "LottieConverter",
        "-srcfolder", staging_dir,
        "-ov",
        "-format", "UDZO",
        dmg_path
    ]

    print(f"Creating {dmg_path} using hdiutil...")
    result = subprocess.run(cmd)

    # Clean up staging directory
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)

    if result.returncode == 0:
        print("\n==================================================")
        print(" SUCCESS: macOS DMG Disk Image Created!")
        print(f" Location: {dmg_path}")
        print(" Usage:")
        print("   1. Double-click dist/LottieConverter.dmg to open.")
        print("   2. Drag LottieConverter.app into Applications folder.")
        print("   3. (Note for unsigned app) If macOS Gatekeeper blocks opening:")
        print("      Run: xattr -cr /Applications/LottieConverter.app")
        print("      Or Right-click LottieConverter.app -> Open -> Open")
        print("==================================================")
    else:
        print("\nFAILED: hdiutil DMG creation failed.")
        sys.exit(result.returncode)



if __name__ == "__main__":
    build_mac_dmg()
