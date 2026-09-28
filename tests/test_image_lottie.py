"""
Test script for Image Sequence Lottie JSON generation with transparent background.
Renders original video foreground image textures instead of single-color vector fill.
"""

import os
import sys
import base64
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video.reader import VideoReader
from background.detector import BackgroundDetector
from mask.processor import BackgroundRemover
import config


def frame_rgba_to_base64_png(rgba_frame: np.ndarray) -> str:
    """Encodes RGBA numpy frame to base64 PNG data URI string."""
    success, buffer = cv2.imencode('.png', rgba_frame)
    if not success:
        raise RuntimeError("Failed to encode frame to PNG")
    b64_data = base64.b64encode(buffer).decode('ascii')
    return f"data:image/png;base64,{b64_data}"


def create_image_lottie_json(video_path: str, target_fps: float = 15.0, threshold: float = 35.0):
    with VideoReader(video_path) as reader:
        video_info = reader.get_info()
        detector = BackgroundDetector()
        bg_color, _ = detector.validate_multi_frame_background(reader)
        remover = BackgroundRemover(threshold=threshold)

        assets = []
        layers = []
        frame_idx = 0

        for f_idx, timestamp, frame_bgr in reader.extract_sampled_frames(target_fps=target_fps):
            # Create soft alpha mask for smooth edges
            alpha_mask = remover.process_frame(frame_bgr, bg_color)
            
            # Combine original BGR colors + alpha mask to RGBA
            b, g, r = cv2.split(frame_bgr)
            rgba = cv2.merge([r, g, b, alpha_mask])

            png_data_uri = frame_rgba_to_base64_png(rgba)
            asset_id = f"image_frame_{frame_idx}"

            assets.append({
                "id": asset_id,
                "w": video_info["width"],
                "h": video_info["height"],
                "u": "",
                "p": png_data_uri,
                "e": 1
            })

            layer = {
                "ddd": 0,
                "ind": frame_idx + 1,
                "ty": 2,  # Image Layer
                "nm": f"Frame_{frame_idx}",
                "refId": asset_id,
                "sr": 1,
                "ks": {
                    "o": {"a": 0, "k": 100},
                    "r": {"a": 0, "k": 0},
                    "p": {"a": 0, "k": [video_info["width"] / 2, video_info["height"] / 2, 0]},
                    "a": {"a": 0, "k": [video_info["width"] / 2, video_info["height"] / 2, 0]},
                    "s": {"a": 0, "k": [100, 100, 100]}
                },
                "ao": 0,
                "ip": frame_idx,
                "op": frame_idx + 1,
                "st": frame_idx,
                "bm": 0
            }
            layers.append(layer)
            frame_idx += 1

        total_frames = frame_idx

        lottie_doc = {
            "v": "5.7.0",
            "fr": target_fps,
            "ip": 0,
            "op": total_frames,
            "w": video_info["width"],
            "h": video_info["height"],
            "nm": "Transparent Original Video Image Lottie",
            "ddd": 0,
            "assets": assets,
            "layers": layers
        }
        return lottie_doc


if __name__ == "__main__":
    test_video = "input/sample_test.mp4"
    if os.path.exists(test_video):
        lottie = create_image_lottie_json(test_video)
        print(f"Generated Image Lottie JSON with {len(lottie['layers'])} frame layers.")
        import json
        out_file = "lottie-output/sample_image_test.json"
        os.makedirs("lottie-output", exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(lottie, f)
        print(f"Saved to {out_file} ({os.path.getsize(out_file) / 1024:.2f} KB)")
