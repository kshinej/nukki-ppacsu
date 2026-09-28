"""
Video Reader module for video file loading, metadata extraction, and frame sampling.
"""

import os
import cv2
import numpy as np
import config


class VideoReader:
    """Handles video file reading, validation, and frame extraction."""

    def __init__(self, video_path: str):
        self.video_path = video_path
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Input video not found: {video_path}")

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise IOError(f"Unable to read video file: {video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30.0  # Fallback if FPS detection fails

        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.frame_count / self.fps if self.fps > 0 else 0.0

        # Validate video duration limit (<= 10s)
        if self.duration > config.MAX_DURATION_SECONDS:
            self.cap.release()
            raise ValueError(f"Video must be 10 seconds or shorter. (Current: {self.duration:.1f}s)")

    def get_info(self) -> dict:
        """Returns video metadata summary."""
        return {
            "path": self.video_path,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "duration": round(self.duration, 2)
        }

    def read_frame_at_index(self, frame_index: int) -> np.ndarray:
        """Reads a single BGR frame at the given frame index."""
        frame_index = max(0, min(frame_index, self.frame_count - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.cap.read()
        if not ret or frame is None:
            raise IOError(f"Failed to read frame at index {frame_index}")
        return frame

    def read_frame_at_ratio(self, ratio: float) -> np.ndarray:
        """Reads a single BGR frame at a fraction (0.0 to 1.0) of total duration."""
        target_index = int(ratio * (self.frame_count - 1))
        return self.read_frame_at_index(target_index)

    def extract_sampled_frames(self, target_fps: float = config.DEFAULT_TARGET_FPS):
        """
        Yields (frame_index, timestamp_sec, bgr_frame) sampled at target_fps.
        """
        target_fps = min(target_fps, self.fps)
        step = self.fps / target_fps
        current_step = 0.0

        while True:
            target_frame_idx = int(round(current_step))
            if target_frame_idx >= self.frame_count:
                break

            frame = self.read_frame_at_index(target_frame_idx)
            timestamp = target_frame_idx / self.fps
            yield target_frame_idx, timestamp, frame

            current_step += step

    def release(self):
        """Releases VideoCapture resources."""
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
