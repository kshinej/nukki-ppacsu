"""
Frame processor module for scaling, color conversion, and image pre-processing.
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class FrameProcessor:
    """Provides frame utility methods like scaling and preprocessing."""

    @staticmethod
    def compute_target_dimensions(
        orig_w: int,
        orig_h: int,
        target_w: Optional[int] = None,
        target_h: Optional[int] = None,
        scale: float = 1.0
    ) -> Tuple[int, int]:
        """
        Calculates output width and height based on user options.
        Preserves aspect ratio if only width or only height is specified.
        """
        if target_w is not None and target_h is not None:
            return int(target_w), int(target_h)
        elif target_w is not None:
            out_w = int(target_w)
            out_h = max(1, int(round(orig_h * (out_w / orig_w))))
            return out_w, out_h
        elif target_h is not None:
            out_h = int(target_h)
            out_w = max(1, int(round(orig_w * (out_h / orig_h))))
            return out_w, out_h
        elif scale != 1.0:
            out_w = max(1, int(round(orig_w * scale)))
            out_h = max(1, int(round(orig_h * scale)))
            return out_w, out_h
        else:
            return orig_w, orig_h

    @staticmethod
    def resize_frame(frame: np.ndarray, target_width: Optional[int] = None, target_height: Optional[int] = None) -> np.ndarray:
        """
        Resizes frame preserving aspect ratio if only one dimension is supplied.
        """
        if target_width is None and target_height is None:
            return frame

        h, w = frame.shape[:2]

        if target_width is not None and target_height is None:
            target_height = max(1, int(round(h * (target_width / w))))
        elif target_height is not None and target_width is None:
            target_width = max(1, int(round(w * (target_height / h))))

        return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)

    @staticmethod
    def bgr_to_hsv(frame: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    @staticmethod
    def bgr_to_lab(frame: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

    @staticmethod
    def bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
