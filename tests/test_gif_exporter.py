"""
Test script for Transparent Animated GIF Exporter.
"""

import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video.reader import VideoReader
from background.detector import BackgroundDetector
from mask.processor import BackgroundRemover
import config


def export_gif(rgba_frames, output_path, fps=15.0):
    duration_ms = int(1000.0 / fps)
    pil_frames = []

    for rgba in rgba_frames:
        # Convert RGBA numpy array to PIL Image
        img_rgba = Image.fromarray(rgba, mode='RGBA')
        alpha = img_rgba.split()[3]

        # Extract RGB and quantize to 255 colors
        img_rgb = img_rgba.convert('RGB')
        img_p = img_rgb.convert('P', palette=Image.ADAPTIVE, colors=255)

        # Mark pixels where alpha < 128 as transparent index (255)
        transparent_mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
        img_p.paste(255, transparent_mask)
        img_p.info['transparency'] = 255
        pil_frames.append(img_p)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pil_frames[0].save(
        output_path,
        format='GIF',
        save_all=True,
        append_images=pil_frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2
    )
    print(f"GIF saved: {output_path} ({os.path.getsize(output_path)/1024:.2f} KB)")
    return output_path


def run_gif_test():
    video_path = "input/sample_test.mp4"
    output_gif = "lottie-output/sample_test.gif"

    with VideoReader(video_path) as reader:
        detector = BackgroundDetector()
        bg_color, _ = detector.validate_multi_frame_background(reader)
        remover = BackgroundRemover(threshold=35.0)

        rgba_frames = []
        for f_idx, ts, frame in reader.extract_sampled_frames(target_fps=15):
            rgba = remover.extract_rgba_foreground(frame, bg_color, threshold=35.0, soft=True)
            rgba_frames.append(rgba)

        export_gif(rgba_frames, output_gif, fps=15)


if __name__ == "__main__":
    run_gif_test()
