"""
Phase 1 & 2 Verification Test Script.
Creates a synthetic test video with a solid background, runs detection, mask creation,
contour extraction, and saves debug images into debug/ directory.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cv2
import numpy as np
from video.reader import VideoReader
from background.detector import BackgroundDetector
from mask.processor import BackgroundRemover
from contour.extractor import ContourExtractor
import config


def create_synthetic_test_video(output_path: str = "input/sample_test.mp4", duration: float = 2.0, fps: int = 30):
    """Generates a synthetic MP4 video featuring a green background and a moving star/polygon object."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    width, height = 640, 480
    num_frames = int(duration * fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Green background (BGR: 0, 255, 0) with slight compression noise simulation
    for i in range(num_frames):
        # Create solid green frame with minor random noise
        frame = np.full((height, width, 3), (10, 245, 15), dtype=np.uint8)

        # Draw a moving star/polygon foreground object (blueish object)
        center_x = int(100 + (width - 200) * (i / num_frames))
        center_y = int(240 + 50 * np.sin(i * 0.2))

        # Star vertices relative to center
        pts = np.array([
            [center_x, center_y - 60],
            [center_x + 20, center_y - 20],
            [center_x + 60, center_y - 20],
            [center_x + 30, center_y + 10],
            [center_x + 40, center_y + 50],
            [center_x, center_y + 30],
            [center_x - 40, center_y + 50],
            [center_x - 30, center_y + 10],
            [center_x - 60, center_y - 20],
            [center_x - 20, center_y - 20]
        ], np.int32)

        # Draw filled blue star
        cv2.fillPoly(frame, [pts], (220, 100, 20))
        out.write(frame)

    out.release()
    print(f"Synthetic test video created: {output_path} ({duration}s, {fps}fps)")
    return output_path


def run_phase1_2_test():
    video_path = create_synthetic_test_video()
    os.makedirs(config.DEBUG_DIR, exist_ok=True)

    print("\n--- Running Phase 1 & 2 Test ---")
    with VideoReader(video_path) as reader:
        print("Video Metadata:", reader.get_info())

        detector = BackgroundDetector()
        bg_color, is_consistent = detector.validate_multi_frame_background(reader)
        detector.print_detection_log(bg_color)

        remover = BackgroundRemover(threshold=config.BACKGROUND_THRESHOLD)
        contour_extractor = ContourExtractor()

        # Save first frame background sample
        frame0 = reader.read_frame_at_index(0)
        cv2.imwrite(os.path.join(config.DEBUG_DIR, "background_sample.png"), frame0)

        # Sample frame 0 and frame 15
        for idx in [0, 15]:
            frame = reader.read_frame_at_index(idx)

            # Generate Mask
            mask = remover.process_frame(frame, bg_color)
            cv2.imwrite(os.path.join(config.DEBUG_DIR, f"mask_{idx:04d}.png"), mask)

            # Extract Contours
            contours = contour_extractor.extract_and_simplify(mask)
            print(f"Frame {idx}: Found {len(contours)} contours.")
            for c_i, c in enumerate(contours):
                print(f"  Contour {c_i}: {len(c)} points after simplification.")

            # Draw & save debug contour image
            contour_img = contour_extractor.draw_contours_debug(frame.shape, contours, mask)
            cv2.imwrite(os.path.join(config.DEBUG_DIR, f"contour_{idx:04d}.png"), contour_img)

    print("\nPhase 1 & 2 test completed. Debug files saved in 'debug/' folder.")


if __name__ == "__main__":
    run_phase1_2_test()
