"""
Main CLI Entry Point for Solid Background Removal to Lottie JSON and Animated GIF Converter.
Supports Lottie (.json) and GIF (.gif) export formats.
"""

import sys
import os
import argparse
import cv2
from typing import List, Tuple, Optional

import config
from video.reader import VideoReader
from video.frame_processor import FrameProcessor
from background.detector import BackgroundDetector
from mask.processor import BackgroundRemover
from contour.extractor import ContourExtractor
from lottie.path import LottiePathConverter
from lottie.writer import LottieWriter
from gif.writer import GifWriter


def parse_hex_color(hex_str: str) -> List[float]:
    """Converts hex color string (#RRGGBB or #RRGGBBAA) to [R, G, B, A] floats (0.0~1.0)."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return [round(r, 3), round(g, 3), round(b, 3), 1.0]
    elif len(hex_str) == 8:
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        a = int(hex_str[6:8], 16) / 255.0
        return [round(r, 3), round(g, 3), round(b, 3), round(a, 3)]
    else:
        raise ValueError(f"Invalid hex color format: '{hex_str}'. Expected #RRGGBB or #RRGGBBAA.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert short solid-background videos (MP4/MOV) to transparent Lottie JSON and animated GIFs."
    )
    parser.add_argument("input", type=str, help="Path to input video file (.mp4 / .mov)")
    parser.add_argument("-o", "--output", type=str, default=None, help="Path for output file (without extension or custom path)")
    parser.add_argument("--format", type=str, choices=["lottie", "gif", "both"], default="both", help="Export format: 'lottie' (.json), 'gif' (.gif), or 'both' (default: both)")
    parser.add_argument("--mode", type=str, choices=["image", "vector"], default="image", help="Output mode: 'image' (Original video colors/texture with transparent BG) or 'vector' (Flat shape silhouette)")
    parser.add_argument("--fps", type=float, default=config.DEFAULT_TARGET_FPS, help="Target FPS for output (default: 15)")
    parser.add_argument("--threshold", type=float, default=config.BACKGROUND_THRESHOLD, help="Background color distance threshold (default: 35)")
    parser.add_argument("--edge-trim", type=int, default=config.DEFAULT_EDGE_TRIM, help="Pixels to shrink mask inward (0~5px) to slice off dark/green border halos")
    parser.add_argument("--edge-blur", type=int, default=config.DEFAULT_EDGE_BLUR, help="Gaussian feathering blur radius (0~7px) for smooth edges")
    parser.add_argument("--epsilon", type=float, default=config.CONTOUR_EPSILON_RATIO, help="Contour simplification ratio (vector mode)")
    parser.add_argument("--min-area", type=float, default=config.MIN_CONTOUR_AREA_RATIO, help="Minimum contour area ratio")
    parser.add_argument("--fill-color", type=str, default="#FFFFFF", help="RGBA fill color in hex for vector mode")
    parser.add_argument("--width", type=int, default=None, help="Target output width in pixels")
    parser.add_argument("--height", type=int, default=None, help="Target output height in pixels")
    parser.add_argument("--scale", type=float, default=1.0, help="Output resolution scale factor")
    parser.add_argument("--debug", action="store_true", help="Save debug mask and contour images into debug/ folder")
    parser.add_argument("--no-optimize", action="store_true", help="Disable duplicate keyframe optimization")

    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"Error: Input video not found: {input_path}")
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_dir = os.path.abspath(config.OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    try:
        fill_rgba = parse_hex_color(args.fill_color)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"\n[1/6] Reading video: {input_path}...")
    try:
        reader = VideoReader(input_path)
    except ValueError as ve:
        print(f"Error: {ve}")
        sys.exit(1)
    except IOError as ie:
        print(f"Error: Unable to read video. Details: {ie}")
        sys.exit(1)

    video_info = reader.get_info()

    print("[2/6] Detecting background color...")
    detector = BackgroundDetector()
    try:
        bg_color, is_consistent = detector.validate_multi_frame_background(reader)
    except Exception as e:
        print(f"Error: Unable to reliably detect a uniform background color. ({e})")
        reader.release()
        sys.exit(1)

    rgb = bg_color["rgb"]

    print(f"[3/6] Removing background (Format: {args.format.upper()}, Mode: {args.mode.upper()})...")
    remover = BackgroundRemover(
        threshold=args.threshold,
        edge_trim=args.edge_trim,
        edge_blur=args.edge_blur
    )

    out_w, out_h = FrameProcessor.compute_target_dimensions(
        video_info["width"],
        video_info["height"],
        target_w=args.width,
        target_h=args.height,
        scale=args.scale
    )
    print(f"  - Input Video Dimensions: {video_info['width']}x{video_info['height']}")
    print(f"  - Target Output Dimensions: {out_w}x{out_h}")

    sampled_rgba_frames = []
    all_frame_contours = []

    print(f"[4/6] Processing frames at target FPS={args.fps}...")
    if args.mode == "image" or args.format in ["gif", "both"]:
        for frame_idx, timestamp, frame in reader.extract_sampled_frames(target_fps=args.fps):
            rgba = remover.extract_rgba_foreground(frame, bg_color, threshold=args.threshold, soft=True)
            sampled_rgba_frames.append(rgba)
            if args.mode == "vector":
                mask = remover.process_frame(frame, bg_color)
                extractor = ContourExtractor(min_area_ratio=args.min_area, epsilon_ratio=args.epsilon)
                contours = extractor.extract_and_simplify(mask)
                all_frame_contours.append(contours)

            if args.debug and len(sampled_rgba_frames) == 1:
                os.makedirs(config.DEBUG_DIR, exist_ok=True)
                cv2.imwrite(os.path.join(config.DEBUG_DIR, "foreground_rgba_sample.png"), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))

    else:
        extractor = ContourExtractor(min_area_ratio=args.min_area, epsilon_ratio=args.epsilon)
        for frame_idx, timestamp, frame in reader.extract_sampled_frames(target_fps=args.fps):
            mask = remover.process_frame(frame, bg_color)
            contours = extractor.extract_and_simplify(mask)
            all_frame_contours.append(contours)

    reader.release()

    print("[5/6] Exporting files...")
    exported_files = []

    # Export GIF if selected
    if args.format in ["gif", "both"]:
        gif_path = os.path.join(output_dir, f"{base_name}.gif") if args.output is None or not args.output.endswith(".gif") else args.output
        GifWriter.save_gif(sampled_rgba_frames, gif_path, fps=args.fps, target_width=out_w, target_height=out_h)
        exported_files.append(gif_path)

    # Export Lottie JSON if selected
    if args.format in ["lottie", "both"]:
        lottie_path = os.path.join(output_dir, f"{base_name}.json") if args.output is None or not args.output.endswith(".json") else args.output
        writer = LottieWriter(
            width=out_w,
            height=out_h,
            fps=args.fps,
            fill_color=fill_rgba,
            optimize_keyframes=not args.no_optimize
        )
        if args.mode == "image":
            lottie_dict = writer.create_image_lottie_dict(sampled_rgba_frames)
        else:
            converter = LottiePathConverter(precision=config.COORDINATE_PRECISION, scale_x=out_w / video_info["width"], scale_y=out_h / video_info["height"])
            lottie_dict = writer.create_lottie_dict(all_frame_contours, converter)

        writer.save_lottie_json(lottie_dict, lottie_path)
        exported_files.append(lottie_path)

    print("\n[6/6] Completed!")
    print("Background:")
    print(f"RGB({rgb[0]},{rgb[1]},{rgb[2]})")

    print("\nExported Files:")
    for f in exported_files:
        print(f" - {f}")

    print("\nFinished successfully.")


if __name__ == "__main__":
    main()
