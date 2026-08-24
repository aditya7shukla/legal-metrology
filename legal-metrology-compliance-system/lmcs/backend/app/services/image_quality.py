"""Non-legal image-quality signals used to guide label capture."""
from __future__ import annotations

import cv2
import numpy as np


def assess_image_quality(path: str) -> dict:
    image = cv2.imread(path)
    if image is None:
        return {"status": "unavailable", "warnings": ["The image could not be assessed."], "metrics": {}}

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Bright, low-saturation patches are a useful reflection signal on shiny packs.
    highlight_ratio = float(np.mean((hsv[:, :, 2] > 245) & (hsv[:, :, 1] < 35)))

    warnings: list[str] = []
    if min(width, height) < 700:
        warnings.append("Low image resolution. Move closer so label text fills more of the frame.")
    if blur_score < 45:
        warnings.append("The image may be blurred. Hold the camera steady and refocus on the text.")
    if highlight_ratio > 0.18:
        warnings.append("Strong glare/reflection detected. Take a second image with indirect light or a different angle.")

    return {
        "status": "needs_attention" if warnings else "good",
        "warnings": warnings,
        "metrics": {"width_px": width, "height_px": height, "blur_score": round(blur_score, 1), "highlight_ratio": round(highlight_ratio, 3)},
    }
