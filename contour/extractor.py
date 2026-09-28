"""
Contour extraction and simplification module.
Extracts vector contours from binary masks and simplifies them with approxPolyDP.
"""

import cv2
import numpy as np
import config
from typing import List, Tuple, Optional


class ContourExtractor:
    """Extracts, filters, and simplifies contours from binary masks."""

    def __init__(
        self,
        min_area_ratio: float = config.MIN_CONTOUR_AREA_RATIO,
        epsilon_ratio: float = config.CONTOUR_EPSILON_RATIO
    ):
        self.min_area_ratio = min_area_ratio
        self.epsilon_ratio = epsilon_ratio

    def extract_contours(
        self,
        mask: np.ndarray,
        retrieval_mode: int = cv2.RETR_EXTERNAL
    ) -> List[np.ndarray]:
        """
        Finds contours in mask and filters out small noise components.
        Returns a list of contour point arrays sorted by area descending.
        """
        h, w = mask.shape[:2]
        frame_area = h * w
        min_area = frame_area * self.min_area_ratio

        contours, hierarchy = cv2.findContours(
            mask,
            retrieval_mode,
            cv2.CHAIN_APPROX_SIMPLE
        )

        filtered_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_area:
                filtered_contours.append(cnt)

        # Sort by contour area descending
        filtered_contours.sort(key=cv2.contourArea, reverse=True)
        return filtered_contours

    def simplify_contour(
        self,
        contour: np.ndarray,
        epsilon_ratio: Optional[float] = None
    ) -> np.ndarray:
        """
        Simplifies contour points using cv2.approxPolyDP.
        Target: ~100 to 300 points per contour while preserving detail.
        """
        if epsilon_ratio is None:
            epsilon_ratio = self.epsilon_ratio

        arc_len = cv2.arcLength(contour, closed=True)
        epsilon = max(1.0, arc_len * epsilon_ratio)

        simplified = cv2.approxPolyDP(contour, epsilon, closed=True)

        # Ensure simplified contour keeps at least 3 points
        if len(simplified) < 3:
            return contour

        return simplified

    def extract_and_simplify(
        self,
        mask: np.ndarray,
        retrieval_mode: int = cv2.RETR_EXTERNAL,
        epsilon_ratio: Optional[float] = None
    ) -> List[np.ndarray]:
        """
        Full pipeline: Find contours -> Filter small noise -> Simplify points.
        """
        raw_contours = self.extract_contours(mask, retrieval_mode)
        simplified_contours = [
            self.simplify_contour(cnt, epsilon_ratio) for cnt in raw_contours
        ]
        return simplified_contours

    @staticmethod
    def draw_contours_debug(
        shape: Tuple[int, int, int],
        contours: List[np.ndarray],
        mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Renders contours onto a debug BGR canvas for Phase 2 inspection.
        """
        h, w = shape[:2]
        canvas = np.zeros((h, w, 3), dtype=np.uint8)

        if mask is not None:
            # Draw semi-transparent background mask preview
            canvas[mask > 0] = (40, 40, 40)

        # Draw simplified contour lines
        for idx, cnt in enumerate(contours):
            color = (0, 255, 0) if idx == 0 else (255, 200, 0)
            cv2.drawContours(canvas, [cnt], -1, color, 2)

            # Draw vertices as small red dots
            for pt in cnt:
                x, y = pt[0]
                cv2.circle(canvas, (int(x), int(y)), 2, (0, 0, 255), -1)

        return canvas
