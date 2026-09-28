"""
GIF Writer module.
Exports frame sequences (with transparent background) to animated GIF files.
"""

import os
import cv2
import numpy as np
from PIL import Image
from typing import List, Optional


class GifWriter:
    """Exports RGBA frame sequences to transparent animated GIF files."""

    @staticmethod
    def save_gif(
        rgba_frames: List[np.ndarray],
        output_path: str,
        fps: float = 15.0,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None
    ) -> str:
        """
        Saves a list of RGBA numpy frames to a transparent animated GIF.
        """
        if not rgba_frames:
            raise ValueError("Cannot write GIF: rgba_frames list is empty.")

        duration_ms = int(round(1000.0 / fps))
        pil_frames = []

        for rgba in rgba_frames:
            h, w = rgba.shape[:2]
            if target_width is not None or target_height is not None:
                tw = target_width if target_width is not None else w
                th = target_height if target_height is not None else h
                if (w, h) != (tw, th):
                    rgba = cv2.resize(rgba, (tw, th), interpolation=cv2.INTER_AREA)

            img_rgba = Image.fromarray(rgba, mode='RGBA')
            alpha = img_rgba.split()[3]

            # Quantize RGB channels to 255 colors
            img_rgb = img_rgba.convert('RGB')
            img_p = img_rgb.convert('P', palette=Image.ADAPTIVE, colors=255)

            # Mark background pixels (alpha < 128) with transparent palette index 255
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
            disposal=2  # Restore to background
        )

        file_size_kb = os.path.getsize(output_path) / 1024.0
        print(f"GIF saved: {output_path} ({file_size_kb:.2f} KB)")
        return output_path
