"""
Image preprocessing pipeline for OCR on real-world product label photographs.

The pipeline keeps multiple OCR-friendly representations instead of forcing
Tesseract to work from a single aggressive binary image.

Designed for:
- product packaging
- uneven lighting
- glossy/reflective plastic
- small printed declarations
- wrinkles and mild perspective distortion
"""

from __future__ import annotations

import cv2
import numpy as np


def load_image(path: str) -> np.ndarray:
    """Load an image from disk."""
    image = cv2.imread(path)

    if image is None:
        raise ValueError(
            f"Could not read image at {path}. "
            "File may be corrupt or unsupported."
        )

    return image


def estimate_skew_angle(gray: np.ndarray) -> float:
    """
    Estimate text skew conservatively.

    The previous implementation used all thresholded pixels in the entire
    photograph. Product photographs contain barcodes, QR codes, graphics and
    package edges, which can produce incorrect rotation estimates.

    We therefore only accept a small angle when there is enough evidence.
    """
    try:
        # Light blur removes tiny noise before edge detection.
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        edges = cv2.Canny(blurred, 50, 150)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=80,
            minLineLength=max(80, gray.shape[1] // 8),
            maxLineGap=20,
        )

        if lines is None:
            return 0.0

        angles: list[float] = []

        for line in lines[:, 0]:
            x1, y1, x2, y2 = map(int, line)

            dx = x2 - x1
            dy = y2 - y1

            if dx == 0:
                continue

            angle = np.degrees(np.arctan2(dy, dx))

            # Keep only lines that are reasonably horizontal.
            if -20 <= angle <= 20:
                angles.append(float(angle))

        if len(angles) < 3:
            return 0.0

        # Median is more robust than one dominant noisy line.
        angle = float(np.median(angles))

        if abs(angle) > 5:
            return 0.0

        return angle

    except Exception:
        # OCR should never fail just because skew estimation failed.
        return 0.0


def deskew(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image by a small estimated skew angle."""
    if abs(angle) < 0.2:
        return image

    height, width = image.shape[:2]
    center = (width // 2, height // 2)

    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def upscale_image(image: np.ndarray, scale: float = 2.5) -> np.ndarray:
    """
    Upscale the image before OCR.

    Small package declarations benefit significantly from having more pixels
    available to Tesseract.
    """
    height, width = image.shape[:2]

    new_width = int(width * scale)
    new_height = int(height * scale)

    return cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_CUBIC,
    )


def enhance_grayscale(gray: np.ndarray) -> np.ndarray:
    """
    Produce a clean grayscale OCR image.

    This is intentionally preferred over aggressive thresholding because
    reflective plastic packaging can lose character information after
    binarization.
    """
    # Mild denoising.
    denoised = cv2.fastNlMeansDenoising(
        gray,
        None,
        h=7,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    # Local contrast enhancement.
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(denoised)

    # Mild unsharp masking.
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 1.2)

    sharpened = cv2.addWeighted(
        enhanced,
        1.35,
        blurred,
        -0.35,
        0,
    )

    return cv2.normalize(
        sharpened,
        None,
        0,
        255,
        cv2.NORM_MINMAX,
    )


def make_otsu_variant(gray: np.ndarray) -> np.ndarray:
    """Create a conservative Otsu binary OCR candidate."""
    return cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]


def make_adaptive_variant(gray: np.ndarray) -> np.ndarray:
    """
    Create an adaptive-threshold candidate.

    This is retained as a secondary OCR candidate, NOT the primary image.
    """
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        41,
        9,
    )


def preprocess_for_ocr(path: str) -> dict:
    """
    Prepare a product photograph for OCR.

    Returns:
        original:
            Original BGR image.

        ocr_ready:
            Primary enhanced grayscale image.

        ocr_variants:
            Additional OCR candidates.

        gray_for_measurement:
            Enhanced grayscale image.

        skew_angle_deg:
            Estimated skew.

        width_px / height_px:
            Original image dimensions.
    """
    original = load_image(path)

    original_height, original_width = original.shape[:2]

    original_gray = cv2.cvtColor(
        original,
        cv2.COLOR_BGR2GRAY,
    )

    angle = estimate_skew_angle(original_gray)

    rotated = deskew(
        original,
        angle,
    )

    rotated_gray = cv2.cvtColor(
        rotated,
        cv2.COLOR_BGR2GRAY,
    )

    # Important: upscale AFTER deskewing.
    upscaled_gray = upscale_image(
        rotated_gray,
        scale=2.5,
    )

    enhanced = enhance_grayscale(
        upscaled_gray,
    )

    otsu = make_otsu_variant(
        enhanced,
    )

    adaptive = make_adaptive_variant(
        enhanced,
    )

    return {
        "original": original,

        # Primary OCR image.
        # We intentionally use grayscale rather than adaptive threshold.
        "ocr_ready": enhanced,

        # Secondary OCR candidates.
        "ocr_variants": [
            enhanced,
            otsu,
            adaptive,
        ],

        "gray_for_measurement": enhanced,

        "skew_angle_deg": angle,

        # Keep measurements tied to the original photograph.
        "height_px": original_height,
        "width_px": original_width,
    }