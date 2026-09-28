"""
Diagnostic test for fixing dark border halos on black background videos.
Tests Mask Erosion (Edge Trim), Edge Feathering, and Color De-spill.
"""

import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video.reader import VideoReader
from background.detector import BackgroundDetector
from mask.processor import BackgroundRemover
import config


def test_black_bg_edge_fix():
    video_path = "input/test4_black.mp4"
    if not os.path.exists(video_path):
        print("Creating black background test video...")
        from tests.test_all_backgrounds import create_scenario_video
        create_scenario_video("test4_black.mp4", (5, 5, 5))

    with VideoReader(video_path) as reader:
        detector = BackgroundDetector()
        bg_color, _ = detector.validate_multi_frame_background(reader)
        remover = BackgroundRemover(threshold=35.0)

        frame = reader.read_frame_at_index(0)

        # Method 1: Standard Mask
        raw_mask = remover.process_frame(frame, bg_color)

        # Method 2: Mask Erosion (1px trim)
        kernel1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        eroded_mask1 = cv2.erode(raw_mask, kernel1, iterations=1)

        # Method 3: Mask Erosion (2px trim)
        kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        eroded_mask2 = cv2.erode(raw_mask, kernel2, iterations=1)

        # Method 4: Erode + Feather (Smooth Blur)
        feather_mask = cv2.GaussianBlur(eroded_mask1, (5, 5), 0)

        # Compare RGBA outputs
        os.makedirs("debug", exist_ok=True)
        b, g, r = cv2.split(frame)

        cv2.imwrite("debug/black_bg_raw.png", cv2.merge([b, g, r, raw_mask]))
        cv2.imwrite("debug/black_bg_erode1.png", cv2.merge([b, g, r, eroded_mask1]))
        cv2.imwrite("debug/black_bg_erode2.png", cv2.merge([b, g, r, eroded_mask2]))
        cv2.imwrite("debug/black_bg_feather.png", cv2.merge([b, g, r, feather_mask]))

        print("Edge fix diagnostic images saved to 'debug/' folder:")
        print(" - debug/black_bg_raw.png (Original halo)")
        print(" - debug/black_bg_erode1.png (1px Edge Trim)")
        print(" - debug/black_bg_erode2.png (2px Edge Trim)")
        print(" - debug/black_bg_feather.png (Erode + Feather)")


if __name__ == "__main__":
    test_black_bg_edge_fix()
