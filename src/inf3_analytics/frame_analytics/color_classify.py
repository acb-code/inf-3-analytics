"""Hardhat color classification from cropped bounding box regions.

Two approaches:
1. HSV histogram (free, fast, ~85-90% accuracy)
2. VLM classification (optional, ~95%+ accuracy, small cost)
"""

import logging
from pathlib import Path
from typing import Any

from inf3_analytics.types.detection import BoundingBox, HardhatColor

LOGGER = logging.getLogger(__name__)

# HSV ranges for hardhat colors (H: 0-179, S: 0-255, V: 0-255 in OpenCV)
# Each entry is (h_low, h_high, s_min, v_min)
_HSV_RANGES: list[tuple[HardhatColor, tuple[int, int], int, int]] = [
    # White: low saturation, high value
    (HardhatColor.WHITE, (0, 179), 0, 180),  # special: s < 60
    # Yellow: H ~20-35
    (HardhatColor.YELLOW, (20, 35), 80, 80),
    # Orange: H ~10-20
    (HardhatColor.ORANGE, (10, 20), 80, 80),
    # Red: H ~0-10 or ~170-179
    (HardhatColor.RED, (0, 10), 80, 80),
    # Blue: H ~100-130
    (HardhatColor.BLUE, (100, 130), 50, 50),
    # Green: H ~35-85
    (HardhatColor.GREEN, (35, 85), 50, 50),
]


def classify_color_histogram(
    image_path: Path | str,
    bbox: BoundingBox,
) -> HardhatColor:
    """Classify hardhat color using HSV histogram on the cropped bbox region.

    Args:
        image_path: Path to the full frame image
        bbox: Normalized bounding box of the hardhat

    Returns:
        Classified HardhatColor
    """
    try:
        import cv2
        import numpy as np
    except ImportError as e:
        raise ImportError(
            "opencv-python and numpy are required. Install with: uv sync --extra cv"
        ) from e

    img = cv2.imread(str(image_path))
    if img is None:
        LOGGER.warning("Could not read image: %s", image_path)
        return HardhatColor.OTHER

    h, w = img.shape[:2]

    # Crop to bbox (normalized coords)
    x1 = max(0, int(bbox.x * w))
    y1 = max(0, int(bbox.y * h))
    x2 = min(w, int((bbox.x + bbox.w) * w))
    y2 = min(h, int((bbox.y + bbox.h) * h))

    if x2 <= x1 or y2 <= y1:
        return HardhatColor.OTHER

    crop = img[y1:y2, x1:x2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    # Compute mean HSV
    mean_h = float(np.mean(hsv[:, :, 0]))
    mean_s = float(np.mean(hsv[:, :, 1]))
    mean_v = float(np.mean(hsv[:, :, 2]))

    # White detection: low saturation, high value
    if mean_s < 60 and mean_v > 180:
        return HardhatColor.WHITE

    # Check each color range by hue
    best_color = HardhatColor.OTHER
    best_score = 0.0

    for color, (h_low, h_high), s_min, v_min in _HSV_RANGES:
        if color == HardhatColor.WHITE:
            continue  # Already handled above

        if mean_s < s_min or mean_v < v_min:
            continue

        # Check if hue falls in range
        if h_low <= mean_h <= h_high:
            # Score by saturation (more saturated = more confident)
            score = mean_s / 255.0
            if score > best_score:
                best_score = score
                best_color = color

    # Special case for red (wraps around H=0)
    if best_color == HardhatColor.OTHER and mean_s >= 80 and mean_v >= 80:
        if mean_h >= 170 or mean_h <= 10:
            best_color = HardhatColor.RED

    return best_color


def classify_color_vlm(
    image_path: Path | str,
    bbox: BoundingBox,
    *,
    client: Any,
    model: str = "gemini-3-flash-preview",
) -> HardhatColor:
    """Classify hardhat color by sending cropped region to Gemini Flash.

    Args:
        image_path: Path to the full frame image
        bbox: Normalized bounding box of the hardhat
        client: Initialized google.genai.Client
        model: Model name for Gemini

    Returns:
        Classified HardhatColor
    """
    try:
        import cv2
    except ImportError as e:
        raise ImportError(
            "opencv-python is required. Install with: uv sync --extra cv"
        ) from e

    img = cv2.imread(str(image_path))
    if img is None:
        LOGGER.warning("Could not read image: %s", image_path)
        return HardhatColor.OTHER

    h, w = img.shape[:2]

    # Crop to bbox with padding
    pad = 0.1  # 10% padding
    x1 = max(0, int((bbox.x - pad * bbox.w) * w))
    y1 = max(0, int((bbox.y - pad * bbox.h) * h))
    x2 = min(w, int((bbox.x + bbox.w + pad * bbox.w) * w))
    y2 = min(h, int((bbox.y + bbox.h + pad * bbox.h) * h))

    if x2 <= x1 or y2 <= y1:
        return HardhatColor.OTHER

    crop = img[y1:y2, x1:x2]

    # Encode as JPEG bytes
    success, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        return HardhatColor.OTHER

    image_bytes = buf.tobytes()

    try:
        from google.genai import types

        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            types.Part.from_text(
                text="What color is the hardhat in this image? "
                "Reply with exactly one word: white, yellow, orange, red, blue, or green."
            ),
        ]

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=10),
        )

        color_str = (response.text or "").strip().lower()
        color_map: dict[str, HardhatColor] = {
            "white": HardhatColor.WHITE,
            "yellow": HardhatColor.YELLOW,
            "orange": HardhatColor.ORANGE,
            "red": HardhatColor.RED,
            "blue": HardhatColor.BLUE,
            "green": HardhatColor.GREEN,
        }
        return color_map.get(color_str, HardhatColor.OTHER)

    except Exception as e:
        LOGGER.warning("VLM color classification failed: %s", e)
        return HardhatColor.OTHER
