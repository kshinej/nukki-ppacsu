"""
Background color detection module.
Samples 4 corners of video frames to determine dominant background color without AI.
"""

import cv2
import numpy as np
import config
from typing import Dict, Tuple, List, Optional


class BackgroundDetector:
    """Detects and validates solid background colors from video corners."""

    def __init__(self, corner_ratio: float = config.CORNER_SAMPLE_RATIO):
        self.corner_ratio = corner_ratio

    def sample_corner_pixels(self, frame: np.ndarray) -> np.ndarray:
        """
        Samples pixels from 4 corner patches (top-left, top-right, bottom-left, bottom-right).
        Returns BGR pixels array of shape (N, 3).
        """
        h, w = frame.shape[:2]
        kh = max(1, int(h * self.corner_ratio))
        kw = max(1, int(w * self.corner_ratio))

        top_left = frame[0:kh, 0:kw]
        top_right = frame[0:kh, w - kw:w]
        bottom_left = frame[h - kh:h, 0:kw]
        bottom_right = frame[h - kh:h, w - kw:w]

        corner_pixels = np.vstack([
            top_left.reshape(-1, 3),
            top_right.reshape(-1, 3),
            bottom_left.reshape(-1, 3),
            bottom_right.reshape(-1, 3)
        ])
        return corner_pixels

    def detect_background_color(self, frame: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Analyzes sampled corner pixels and returns representative background colors
        in BGR, RGB, HSV, and LAB color spaces.
        """
        corner_bgr = self.sample_corner_pixels(frame)

        # Convert sampled BGR pixels to LAB and HSV for robust color estimation
        corner_bgr_img = corner_bgr.reshape(-1, 1, 3)
        corner_lab = cv2.cvtColor(corner_bgr_img, cv2.COLOR_BGR2LAB).reshape(-1, 3)
        corner_hsv = cv2.cvtColor(corner_bgr_img, cv2.COLOR_BGR2HSV).reshape(-1, 3)

        # Calculate spatial median in LAB color space (robust to corner noise/shadows)
        lab_median = np.median(corner_lab, axis=0).astype(np.uint8)

        # Map median LAB back to BGR/RGB/HSV
        lab_pixel = np.uint8([[lab_median]])
        bgr_bg = cv2.cvtColor(lab_pixel, cv2.COLOR_LAB2BGR)[0, 0]
        bgr_pixel = np.uint8([[bgr_bg]])
        rgb_bg = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2RGB)[0, 0]
        hsv_bg = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2HSV)[0, 0]

        return {
            "bgr": bgr_bg,
            "rgb": rgb_bg,
            "hsv": hsv_bg,
            "lab": lab_median
        }

    def print_detection_log(self, color_dict: Dict[str, np.ndarray]):
        """Prints background detection results as specified in documentation."""
        rgb = color_dict["rgb"]
        hsv = color_dict["hsv"]
        print("Background color detected:")
        print(f"RGB({rgb[0]}, {rgb[1]}, {rgb[2]})")
        print("HSV:")
        print(f"H={int(hsv[0] * 2)} (OpenCV H={hsv[0]})")
        print(f"S={hsv[1]}")
        print(f"V={hsv[2]}")

    def validate_multi_frame_background(
        self,
        video_reader,
        checkpoints: List[float] = config.VALIDATION_CHECKPOINTS
    ) -> Tuple[Dict[str, np.ndarray], bool]:
        """
        Validates background consistency across multiple checkpoints (e.g. 0%, 25%, 50%, 75%, 100%).
        Returns (primary_color_dict, is_consistent).
        """
        detected_colors = []
        is_consistent = True

        first_bg = None

        for ratio in checkpoints:
            try:
                frame = video_reader.read_frame_at_ratio(ratio)
                color = self.detect_background_color(frame)
                detected_colors.append((ratio, color))

                if first_bg is None:
                    first_bg = color
                else:
                    # Calculate LAB color distance against first frame background
                    lab_diff = np.linalg.norm(
                        color["lab"].astype(float) - first_bg["lab"].astype(float)
                    )
                    if lab_diff > 30.0:  # Noticeable color change threshold
                        is_consistent = False
            except Exception as e:
                print(f"Warning: Failed to read frame at ratio {ratio}: {e}")
                pass

        if first_bg is None:
            raise RuntimeError("Unable to reliably detect a uniform background color.")

        print("\n--- Background Checkpoints ---")
        for ratio, color in detected_colors:
            rgb = color["rgb"]
            pct_str = f"{int(ratio * 100)}%"
            print(f"Frame {pct_str:>4} -> RGB({rgb[0]}, {rgb[1]}, {rgb[2]})")

        if is_consistent:
            print("Background detected successfully.\n")
        else:
            print("Warning:\nBackground color appears to change during the video.\n")

        return first_bg, is_consistent
