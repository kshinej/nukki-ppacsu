"""
Test video duration limit (> 10s error check).
"""

import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video.reader import VideoReader


def test_over_10s_video():
    filepath = "input/over_10s_test.mp4"
    width, height = 320, 240
    fps = 30
    duration = 11.0
    num_frames = int(duration * fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
    for _ in range(num_frames):
        out.write(np.zeros((height, width, 3), dtype=np.uint8))
    out.release()

    try:
        reader = VideoReader(filepath)
        print("FAIL: Did not reject video > 10 seconds.")
    except ValueError as ve:
        print("SUCCESS: Correctly rejected video > 10 seconds.")
        print(f"Error message captured: {ve}")


if __name__ == "__main__":
    test_over_10s_video()
