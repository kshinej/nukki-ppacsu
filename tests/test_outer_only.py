"""
Unit tests for outer_only background removal mode.
Tests that internal shapes/details sharing the background color are preserved
when outer_only=True, and removed when outer_only=False.
"""

import unittest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import cv2
from mask.processor import BackgroundRemover


class TestOuterOnlyBackgroundRemoval(unittest.TestCase):

    def setUp(self):
        # Create 200x200 image with white background (255, 255, 255)
        self.img = np.full((200, 200, 3), 255, dtype=np.uint8)
        # Blue rectangle in center (50:150, 50:150)
        self.img[50:150, 50:150] = [255, 0, 0]
        # White circle inside the blue rectangle (100, 100, radius 20)
        cv2.circle(self.img, (100, 100), 20, (255, 255, 255), -1)

        bg_bgr = np.array([255, 255, 255])
        bg_lab = cv2.cvtColor(np.uint8([[[255, 255, 255]]]), cv2.COLOR_BGR2LAB)[0, 0]
        self.bg_dict = {"bgr": bg_bgr, "lab": bg_lab}

    def test_global_removal_removes_internal_white(self):
        remover = BackgroundRemover(threshold=20.0, edge_trim=0, edge_blur=0, outer_only=False)
        rgba = remover.extract_rgba_foreground(
            self.img, self.bg_dict, threshold=20.0, soft=False, edge_trim=0, edge_blur=0, outer_only=False
        )
        alpha = rgba[:, :, 3]

        # Outer background pixel (10, 10) must be 0 (transparent)
        self.assertEqual(alpha[10, 10], 0)
        # Blue body pixel (60, 60) must be 255 (opaque)
        self.assertEqual(alpha[60, 60], 255)
        # Internal white circle (100, 100) is ALSO removed in global mode
        self.assertEqual(alpha[100, 100], 0)

    def test_outer_only_preserves_internal_white(self):
        remover = BackgroundRemover(threshold=20.0, edge_trim=0, edge_blur=0, outer_only=True)
        rgba = remover.extract_rgba_foreground(
            self.img, self.bg_dict, threshold=20.0, soft=False, edge_trim=0, edge_blur=0, outer_only=True
        )
        alpha = rgba[:, :, 3]

        # Outer background pixel (10, 10) must be 0 (transparent)
        self.assertEqual(alpha[10, 10], 0)
        # Blue body pixel (60, 60) must be 255 (opaque)
        self.assertEqual(alpha[60, 60], 255)
        # Internal white circle (100, 100) MUST BE PROTECTED (255 opaque)!
        self.assertEqual(alpha[100, 100], 255)

    def test_outer_only_binary_mask(self):
        remover = BackgroundRemover(threshold=20.0, edge_trim=0, edge_blur=0, outer_only=True)
        mask = remover.create_binary_mask(self.img, self.bg_dict["lab"], threshold=20.0, outer_only=True)

        self.assertEqual(mask[10, 10], 0)
        self.assertEqual(mask[60, 60], 255)
        self.assertEqual(mask[100, 100], 255)


if __name__ == "__main__":
    unittest.main()
