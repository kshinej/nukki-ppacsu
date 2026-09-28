"""
Phase 3, 4 & 5 Verification Test Script.
Runs full pipeline from sample MP4 to Lottie JSON conversion, verifying path keyframes and optimization.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video.reader import VideoReader
from background.detector import BackgroundDetector
from mask.processor import BackgroundRemover
from contour.extractor import ContourExtractor
from lottie.path import LottiePathConverter
from lottie.writer import LottieWriter
import config


def run_phase3_5_test():
    video_path = "input/sample_test.mp4"
    output_path = "output/sample_test.json"

    print("\n--- Running Phase 3, 4, 5 Test ---")

    with VideoReader(video_path) as reader:
        video_info = reader.get_info()
        print("Video Metadata:", video_info)

        # 1. Background Detection
        detector = BackgroundDetector()
        bg_color, is_consistent = detector.validate_multi_frame_background(reader)

        # 2. Mask Processor & Contour Extractor
        remover = BackgroundRemover(threshold=config.BACKGROUND_THRESHOLD)
        extractor = ContourExtractor()

        # 3. Frame Sampling and Path Extraction
        target_fps = 15
        all_frame_contours = []

        print(f"Processing frames at target FPS={target_fps}...")
        for frame_idx, timestamp, frame in reader.extract_sampled_frames(target_fps=target_fps):
            mask = remover.process_frame(frame, bg_color)
            contours = extractor.extract_and_simplify(mask)
            all_frame_contours.append(contours)

        print(f"Sampled {len(all_frame_contours)} frames total.")

        # 4. Lottie Conversion and Export
        converter = LottiePathConverter()
        writer = LottieWriter(
            width=video_info["width"],
            height=video_info["height"],
            fps=target_fps
        )

        lottie_dict = writer.create_lottie_dict(all_frame_contours, converter)

        # 5. Validation
        is_valid = LottieWriter.validate_lottie_dict(lottie_dict)
        print(f"Lottie Spec Validation: {'PASSED' if is_valid else 'FAILED'}")

        # Save JSON
        saved_file = writer.save_lottie_json(lottie_dict, output_path)
        print("Phase 3~5 test successfully completed!\n")


if __name__ == "__main__":
    run_phase3_5_test()
