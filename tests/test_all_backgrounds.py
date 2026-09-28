"""
Comprehensive Test Suite for 5 Background Color Scenarios (Section 28).
Test 1: Green background + moving shape
Test 2: Blue background + moving shape
Test 3: White background + moving shape
Test 4: Black background + moving shape
Test 5: Red background + multiple moving objects
"""

import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video.reader import VideoReader
from background.detector import BackgroundDetector
from mask.processor import BackgroundRemover
from contour.extractor import ContourExtractor
from lottie.path import LottiePathConverter
from lottie.writer import LottieWriter
import config


def create_scenario_video(filename: str, bg_bgr: Tuple[int, int, int], multi_object: bool = False) -> str:
    filepath = os.path.join("input", filename)
    width, height = 640, 480
    fps = 30
    duration = 2.0
    num_frames = int(duration * fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

    for i in range(num_frames):
        # Create solid background frame
        frame = np.full((height, width, 3), bg_bgr, dtype=np.uint8)

        # Object 1: Moving circle/ellipse
        cx1 = int(120 + (width - 240) * (i / num_frames))
        cy1 = int(240 + 40 * np.cos(i * 0.15))
        # Draw contrast foreground object
        fg_color1 = (255 - bg_bgr[0], 255 - bg_bgr[1], 255 - bg_bgr[2])
        cv2.circle(frame, (cx1, cy1), 45, fg_color1, -1)

        if multi_object:
            # Object 2: Moving rectangle
            cx2 = int(width - 120 - (width - 240) * (i / num_frames))
            cy2 = int(240 - 40 * np.cos(i * 0.15))
            cv2.rectangle(frame, (cx2 - 35, cy2 - 35), (cx2 + 35, cy2 + 35), (0, 255, 255), -1)

        out.write(frame)

    out.release()
    return filepath


def run_all_background_tests():
    scenarios = [
        ("test1_green.mp4", (0, 255, 0), "Green Background + Object", False),
        ("test2_blue.mp4", (255, 0, 0), "Blue Background + Object", False),
        ("test3_white.mp4", (250, 250, 250), "White Background + Object", False),
        ("test4_black.mp4", (5, 5, 5), "Black Background + Object", False),
        ("test5_red_multi.mp4", (0, 0, 255), "Red Background + Multiple Objects", True),
    ]

    print("==================================================")
    print(" Running Comprehensive 5-Scenario Verification")
    print("==================================================")

    all_passed = True

    for filename, bg_bgr, label, multi in scenarios:
        print(f"\n--- {label} ({filename}) ---")
        video_path = create_scenario_video(filename, bg_bgr, multi_object=multi)
        output_json = os.path.join("output", filename.replace(".mp4", ".json"))

        with VideoReader(video_path) as reader:
            video_info = reader.get_info()

            # Detect background
            detector = BackgroundDetector()
            bg_color, is_consistent = detector.validate_multi_frame_background(reader)
            detector.print_detection_log(bg_color)

            # Process mask & contours
            remover = BackgroundRemover(threshold=config.BACKGROUND_THRESHOLD)
            extractor = ContourExtractor()

            all_frame_contours = []
            for f_idx, ts, frame in reader.extract_sampled_frames(target_fps=15):
                mask = remover.process_frame(frame, bg_color)
                contours = extractor.extract_and_simplify(mask)
                all_frame_contours.append(contours)

            # Convert to Lottie
            converter = LottiePathConverter()
            writer = LottieWriter(width=video_info["width"], height=video_info["height"], fps=15)
            lottie_dict = writer.create_lottie_dict(all_frame_contours, converter)

            # Validate Lottie schema
            valid = LottieWriter.validate_lottie_dict(lottie_dict)
            writer.save_lottie_json(lottie_dict, output_json)

            if valid and is_consistent and os.path.exists(output_json):
                print(f"RESULT: PASSED ({len(all_frame_contours)} frames, Lottie output OK)")
            else:
                print("RESULT: FAILED")
                all_passed = False

    print("\n==================================================")
    if all_passed:
        print(" ALL 5 TEST SCENARIOS PASSED SUCCESSFULLY!")
    else:
        print(" SOME TEST SCENARIOS FAILED!")
    print("==================================================")


if __name__ == "__main__":
    run_all_background_tests()
