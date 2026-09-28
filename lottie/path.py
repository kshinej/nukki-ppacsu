"""
Lottie Path converter module.
Converts OpenCV contour point arrays into standard Lottie shape path JSON structures.
"""

import numpy as np
import config
from typing import Dict, List, Any, Tuple, Optional


class LottiePathConverter:
    """Converts vector contours into Lottie Bezier/Polygon path structures."""

    def __init__(
        self,
        precision: int = config.COORDINATE_PRECISION,
        scale_x: float = 1.0,
        scale_y: float = 1.0
    ):
        self.precision = precision
        self.scale_x = scale_x
        self.scale_y = scale_y

    def contour_to_lottie_path(
        self,
        contour: np.ndarray,
        closed: bool = True
    ) -> Dict[str, Any]:
        """
        Converts OpenCV contour array (N, 1, 2) or (N, 2) into Lottie shape dictionary:
        {
          "i": [[0,0], ...],
          "o": [[0,0], ...],
          "v": [[x,y], ...],
          "c": True
        }
        """
        pts = contour.reshape(-1, 2)
        v = []
        i_tangents = []
        o_tangents = []

        for pt in pts:
            x = round(float(pt[0]) * self.scale_x, self.precision)
            y = round(float(pt[1]) * self.scale_y, self.precision)
            v.append([x, y])
            i_tangents.append([0.0, 0.0])
            o_tangents.append([0.0, 0.0])

        return {
            "i": i_tangents,
            "o": o_tangents,
            "v": v,
            "c": closed
        }

    @staticmethod
    def get_empty_lottie_path() -> Dict[str, Any]:
        """Returns a collapsed 0-size dummy path for empty/missing contours."""
        return {
            "i": [[0.0, 0.0]],
            "o": [[0.0, 0.0]],
            "v": [[0.0, 0.0]],
            "c": True
        }

    @staticmethod
    def is_path_similar(
        path1: Dict[str, Any],
        path2: Dict[str, Any],
        tolerance: float = 0.5
    ) -> bool:
        """
        Checks whether path1 and path2 are virtually identical (for keyframe optimization).
        """
        v1 = path1.get("v", [])
        v2 = path2.get("v", [])

        if len(v1) != len(v2):
            return False

        if not v1:
            return True

        arr1 = np.array(v1, dtype=float)
        arr2 = np.array(v2, dtype=float)
        max_diff = np.max(np.abs(arr1 - arr2))
        return bool(max_diff <= tolerance)
