"""
Mask processor module.
Generates background removal masks based on color distance and applies morphological post-processing.
Supports Edge Trim (Erosion) and Edge Blur (Feathering) to eliminate border halos.
"""

import cv2
import numpy as np
import config
from typing import Dict, Tuple


class BackgroundRemover:
    """Computes color distance masks and applies morphological cleaning and edge trim."""

    def __init__(
        self,
        threshold: float = config.BACKGROUND_THRESHOLD,
        morph_kernel_size: int = config.MORPH_KERNEL_SIZE,
        edge_trim: int = config.DEFAULT_EDGE_TRIM,
        edge_blur: int = config.DEFAULT_EDGE_BLUR,
        outer_only: bool = getattr(config, "DEFAULT_OUTER_ONLY", True)
    ):
        self.threshold = threshold
        self.morph_kernel_size = morph_kernel_size
        self.edge_trim = edge_trim
        self.edge_blur = edge_blur
        self.outer_only = outer_only

    def compute_color_distance(self, frame_bgr: np.ndarray, bg_lab: np.ndarray) -> np.ndarray:
        """
        Computes pixel-wise CIELAB color distance from frame to background color.
        Returns 2D float32 distance array.
        """
        frame_lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        bg_lab_target = bg_lab.astype(np.float32)
        diff = frame_lab - bg_lab_target
        dist = np.sqrt(np.sum(diff ** 2, axis=2))
        return dist

    def get_outer_background_mask(
        self,
        frame_bgr: np.ndarray,
        bg_lab: np.ndarray,
        threshold: float = None
    ) -> np.ndarray:
        """
        Identifies pixels matching the background color that are spatially connected
        to the outer boundaries (top, bottom, left, right edges) of the frame.
        Returns a boolean 2D mask (True for outer background, False for foreground/internal).
        """
        if threshold is None:
            threshold = self.threshold

        dist = self.compute_color_distance(frame_bgr, bg_lab)
        candidate_bg = (dist <= threshold).astype(np.uint8)

        num_labels, labels = cv2.connectedComponents(candidate_bg, connectivity=8)
        if num_labels <= 1:
            return np.zeros(frame_bgr.shape[:2], dtype=bool)

        h, w = frame_bgr.shape[:2]
        top_labels = labels[0, :]
        bottom_labels = labels[h - 1, :]
        left_labels = labels[:, 0]
        right_labels = labels[:, w - 1]

        border_labels = np.unique(np.concatenate([top_labels, bottom_labels, left_labels, right_labels]))
        border_labels = border_labels[border_labels > 0]

        if len(border_labels) == 0:
            return np.zeros(frame_bgr.shape[:2], dtype=bool)

        is_border_label = np.zeros(num_labels, dtype=bool)
        is_border_label[border_labels] = True
        is_outer_bg = is_border_label[labels]
        return is_outer_bg

    def create_binary_mask(
        self,
        frame_bgr: np.ndarray,
        bg_lab: np.ndarray,
        threshold: float = None,
        outer_only: bool = None
    ) -> np.ndarray:
        """
        Generates binary mask where 255 = foreground, 0 = background.
        If outer_only is True, only background pixels connected to image borders are removed.
        """
        if threshold is None:
            threshold = self.threshold
        if outer_only is None:
            outer_only = self.outer_only

        if outer_only:
            is_outer_bg = self.get_outer_background_mask(frame_bgr, bg_lab, threshold)
            binary_mask = (~is_outer_bg).astype(np.uint8) * 255
        else:
            dist = self.compute_color_distance(frame_bgr, bg_lab)
            binary_mask = (dist > threshold).astype(np.uint8) * 255
        return binary_mask

    def create_soft_alpha_mask(
        self,
        frame_bgr: np.ndarray,
        bg_lab: np.ndarray,
        threshold: float = None,
        delta: float = config.SOFT_THRESHOLD_DELTA,
        outer_only: bool = None
    ) -> np.ndarray:
        """
        Generates soft alpha mask (0~255) for smooth edge transitions.
        If outer_only is True, internal pixels are protected with full opacity (255).
        """
        if threshold is None:
            threshold = self.threshold
        if outer_only is None:
            outer_only = self.outer_only

        dist = self.compute_color_distance(frame_bgr, bg_lab)
        low = max(0.0, threshold - delta)
        high = threshold + delta

        alpha = np.clip((dist - low) / (high - low) * 255.0, 0, 255).astype(np.uint8)

        if outer_only:
            is_outer_bg = self.get_outer_background_mask(frame_bgr, bg_lab, threshold)
            alpha[~is_outer_bg] = 255

        return alpha

    def post_process_mask(self, binary_mask: np.ndarray) -> np.ndarray:
        """
        Applies morphological OPEN and CLOSE operations to clean up noise and small gaps.
        """
        if self.morph_kernel_size <= 1:
            return binary_mask

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.morph_kernel_size, self.morph_kernel_size)
        )

        cleaned = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        return cleaned

    def apply_edge_cleanup(
        self,
        mask: np.ndarray,
        edge_trim: int = None,
        edge_blur: int = None
    ) -> np.ndarray:
        """
        Shrinks border boundary by edge_trim pixels to slice off compression halos/fringing,
        and optionally applies Gaussian feathering blur.
        """
        if edge_trim is None:
            edge_trim = self.edge_trim
        if edge_blur is None:
            edge_blur = self.edge_blur

        cleaned = mask.copy()

        # 1. Edge Trim / Erosion: Shrink mask inward by N pixels to slice off border halo
        if edge_trim > 0:
            ksize = 2 * edge_trim + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
            cleaned = cv2.erode(cleaned, kernel, iterations=1)

        # 2. Edge Blur / Feathering
        if edge_blur > 0:
            ksize = 2 * edge_blur + 1
            cleaned = cv2.GaussianBlur(cleaned, (ksize, ksize), 0)

        # 3. Alpha noise cutoff
        cleaned[cleaned < 30] = 0

        return cleaned

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        bg_color_dict: Dict[str, np.ndarray],
        threshold: float = None,
        edge_trim: int = None,
        edge_blur: int = None,
        outer_only: bool = None
    ) -> np.ndarray:
        """
        Full mask generation pipeline: BGR Frame -> Binary Mask -> Morphological Cleaning -> Edge Trim.
        """
        if outer_only is None:
            outer_only = self.outer_only
        raw_mask = self.create_binary_mask(frame_bgr, bg_color_dict["lab"], threshold, outer_only=outer_only)
        processed_mask = self.post_process_mask(raw_mask)
        final_mask = self.apply_edge_cleanup(processed_mask, edge_trim, edge_blur)
        return final_mask

    def extract_foreground_preview(
        self,
        frame_bgr: np.ndarray,
        mask: np.ndarray
    ) -> np.ndarray:
        """
        Extracts RGBA image with transparent background for preview/debugging.
        """
        b, g, r = cv2.split(frame_bgr)
        rgba = cv2.merge([r, g, b, mask])
        return rgba

    def extract_rgba_foreground(
        self,
        frame_bgr: np.ndarray,
        bg_color_dict: Dict[str, np.ndarray],
        threshold: float = None,
        soft: bool = True,
        edge_trim: int = None,
        edge_blur: int = None,
        outer_only: bool = None
    ) -> np.ndarray:
        """
        Extracts RGBA frame preserving original video pixel colors for foreground
        and setting transparent alpha=0 for background pixels with edge halo trimming.
        """
        if outer_only is None:
            outer_only = self.outer_only

        b, g, r = cv2.split(frame_bgr)
        if soft:
            alpha = self.create_soft_alpha_mask(frame_bgr, bg_color_dict["lab"], threshold, outer_only=outer_only)
            if self.morph_kernel_size > 1:
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_kernel_size, self.morph_kernel_size))
                alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel)
            alpha = self.apply_edge_cleanup(alpha, edge_trim, edge_blur)
        else:
            alpha = self.process_frame(frame_bgr, bg_color_dict, threshold, edge_trim, edge_blur, outer_only=outer_only)

        rgba = cv2.merge([r, g, b, alpha])
        return rgba

