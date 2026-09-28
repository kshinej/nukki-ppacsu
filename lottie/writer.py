"""
Lottie Writer module.
Assembles frame-by-frame shape path keyframes or image sequence assets into standard Lottie JSON structures.
"""

import json
import os
import base64
import cv2
import numpy as np
import config
from typing import Dict, List, Any, Optional
from lottie.path import LottiePathConverter


class LottieWriter:
    """Assembles and writes Lottie JSON files from frame sequences (Vector or Image mode)."""

    def __init__(
        self,
        width: int,
        height: int,
        fps: float = config.DEFAULT_TARGET_FPS,
        fill_color: Optional[List[float]] = None,
        optimize_keyframes: bool = True
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.fill_color = fill_color if fill_color is not None else config.DEFAULT_FILL_COLOR
        self.optimize_keyframes = optimize_keyframes

    def create_image_lottie_dict(
        self,
        sampled_rgba_frames: List[np.ndarray]
    ) -> Dict[str, Any]:
        """
        Builds Lottie JSON structure embedding original video RGBA frames (with transparent background)
        as image sequence assets, preserving full original colors, textures, and details.
        """
        num_frames = len(sampled_rgba_frames)
        if num_frames == 0:
            raise ValueError("Cannot write Lottie JSON: sampled_rgba_frames is empty.")

        assets = []
        layers = []

        for frame_idx, rgba in enumerate(sampled_rgba_frames):
            fh, fw = rgba.shape[:2]
            if fw != self.width or fh != self.height:
                rgba = cv2.resize(rgba, (self.width, self.height), interpolation=cv2.INTER_AREA)

            success, buffer = cv2.imencode('.png', rgba)
            if not success:
                continue
            b64_data = base64.b64encode(buffer).decode('ascii')
            png_data_uri = f"data:image/png;base64,{b64_data}"
            asset_id = f"img_frame_{frame_idx}"

            assets.append({
                "id": asset_id,
                "w": self.width,
                "h": self.height,
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
                    "p": {"a": 0, "k": [self.width / 2, self.height / 2, 0]},
                    "a": {"a": 0, "k": [self.width / 2, self.height / 2, 0]},
                    "s": {"a": 0, "k": [100, 100, 100]}
                },
                "ao": 0,
                "ip": frame_idx,
                "op": frame_idx + 1,
                "st": frame_idx,
                "bm": 0
            }
            layers.append(layer)

        lottie_doc = {
            "v": "5.7.0",
            "fr": self.fps,
            "ip": 0,
            "op": num_frames,
            "w": self.width,
            "h": self.height,
            "nm": "Original Video Texture Lottie Animation",
            "ddd": 0,
            "assets": assets,
            "layers": layers
        }
        return lottie_doc

    def create_lottie_dict(
        self,
        frame_contours_list: List[List[Any]],
        converter: LottiePathConverter
    ) -> Dict[str, Any]:
        """
        Builds vector contour shape path Lottie JSON structure.
        `frame_contours_list`: List of contour lists for each sampled frame index t=0..N-1.
        """
        num_frames = len(frame_contours_list)
        if num_frames == 0:
            raise ValueError("Cannot write Lottie JSON: frame_contours_list is empty.")

        max_objects = max(len(contours) for contours in frame_contours_list)
        max_objects = max(1, max_objects)

        shape_groups = []

        for obj_idx in range(max_objects):
            path_keyframes = []
            prev_path = None

            for frame_idx, contours in enumerate(frame_contours_list):
                if obj_idx < len(contours):
                    current_path = converter.contour_to_lottie_path(contours[obj_idx])
                else:
                    current_path = LottiePathConverter.get_empty_lottie_path()

                if (
                    self.optimize_keyframes
                    and prev_path is not None
                    and frame_idx < num_frames - 1
                    and LottiePathConverter.is_path_similar(prev_path, current_path)
                ):
                    continue

                keyframe = {
                    "t": frame_idx,
                    "s": [current_path],
                    "h": 1
                }
                path_keyframes.append(keyframe)
                prev_path = current_path

            if len(path_keyframes) == 1:
                ks_prop = {
                    "a": 0,
                    "k": path_keyframes[0]["s"][0]
                }
            else:
                ks_prop = {
                    "a": 1,
                    "k": path_keyframes
                }

            group_item = {
                "ty": "gr",
                "nm": f"Object_{obj_idx + 1}",
                "it": [
                    {
                        "ty": "sh",
                        "nm": f"Path_{obj_idx + 1}",
                        "ks": ks_prop
                    },
                    {
                        "ty": "fl",
                        "nm": "Fill",
                        "c": {
                            "a": 0,
                            "k": self.fill_color
                        },
                        "o": {
                            "a": 0,
                            "k": 100
                        },
                        "r": 1
                    },
                    {
                        "ty": "tr",
                        "nm": "Transform",
                        "p": {"a": 0, "k": [0, 0]},
                        "a": {"a": 0, "k": [0, 0]},
                        "s": {"a": 0, "k": [100, 100]},
                        "r": {"a": 0, "k": 0},
                        "o": {"a": 0, "k": 100}
                    }
                ]
            }
            shape_groups.append(group_item)

        layer = {
            "ddd": 0,
            "ind": 1,
            "ty": 4,  # Shape Layer
            "nm": "Vector Object Layer",
            "sr": 1,
            "ks": {
                "o": {"a": 0, "k": 100},
                "r": {"a": 0, "k": 0},
                "p": {"a": 0, "k": [0, 0, 0]},
                "a": {"a": 0, "k": [0, 0, 0]},
                "s": {"a": 0, "k": [100, 100, 100]}
            },
            "ao": 0,
            "shapes": shape_groups,
            "ip": 0,
            "op": num_frames,
            "st": 0,
            "bm": 0
        }

        lottie_doc = {
            "v": "5.7.0",
            "fr": self.fps,
            "ip": 0,
            "op": num_frames,
            "w": int(self.width * converter.scale_x),
            "h": int(self.height * converter.scale_y),
            "nm": "Solid Background Video Vector Lottie",
            "ddd": 0,
            "assets": [],
            "layers": [layer]
        }
        return lottie_doc

    def save_lottie_json(
        self,
        lottie_dict: Dict[str, Any],
        output_path: str,
        indent: Optional[int] = None
    ) -> str:
        """
        Saves Lottie dictionary to a JSON file.
        Returns the absolute output path.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(lottie_dict, f, ensure_ascii=False, indent=indent)

        file_size_kb = os.path.getsize(output_path) / 1024.0
        print(f"Lottie JSON saved: {output_path} ({file_size_kb:.2f} KB)")
        return output_path

    @staticmethod
    def validate_lottie_dict(lottie_dict: Dict[str, Any]) -> bool:
        """
        Validates presence of essential standard Lottie fields.
        """
        required_keys = ["v", "fr", "ip", "op", "w", "h", "layers"]
        for key in required_keys:
            if key not in lottie_dict:
                print(f"Validation Error: Missing required key '{key}' in Lottie JSON.")
                return False
        if not isinstance(lottie_dict["layers"], list) or len(lottie_dict["layers"]) == 0:
            print("Validation Error: 'layers' must be a non-empty array.")
            return False
        return True
