"""
Robust OCR service for packaged-commodity label photographs.

Strategy:
1. Load the original image.
2. Upscale it.
3. Generate multiple preprocessing variants.
4. Run Tesseract with multiple PSM modes.
5. Run OCR on full image + useful crops.
6. Merge high-quality OCR lines.
7. Preserve bounding boxes and confidence for downstream rules.

This is intentionally multi-pass because a single preprocessing method
is unreliable on reflective, curved, angled product packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import re

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from app.config import settings

if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


ASSUMED_DPI_FALLBACK = 300
MM_PER_INCH = 25.4


@dataclass
class TextLine:
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    block_num: int
    line_num: int


@dataclass
class OcrResult:
    full_text: str
    lines: list[TextLine] = field(default_factory=list)
    image_width_px: int = 0
    image_height_px: int = 0
    skew_angle_deg: float = 0.0


# ---------------------------------------------------------
# IMAGE LOADING
# ---------------------------------------------------------

def load_image(path: str) -> np.ndarray:
    image = cv2.imread(path)

    if image is None:
        raise ValueError(
            f"Could not read image at {path}. "
            "File may be corrupt or unsupported."
        )

    return image


# ---------------------------------------------------------
# BASIC IMAGE PREPARATION
# ---------------------------------------------------------

def upscale(image: np.ndarray, scale: float = 2.5) -> np.ndarray:
    h, w = image.shape[:2]

    return cv2.resize(
        image,
        (int(w * scale), int(h * scale)),
        interpolation=cv2.INTER_CUBIC,
    )


def gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image

    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def clahe_enhance(image: np.ndarray) -> np.ndarray:
    g = gray(image)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    return clahe.apply(g)


def gentle_denoise(image: np.ndarray) -> np.ndarray:
    g = gray(image)

    return cv2.fastNlMeansDenoising(
        g,
        None,
        h=5,
        templateWindowSize=7,
        searchWindowSize=21,
    )


def sharpen(image: np.ndarray) -> np.ndarray:
    g = gray(image)

    blur = cv2.GaussianBlur(g, (0, 0), 1.2)

    return cv2.addWeighted(
        g,
        1.6,
        blur,
        -0.6,
        0,
    )


# ---------------------------------------------------------
# OCR VARIANTS
# ---------------------------------------------------------

def make_variants(image: np.ndarray) -> list[tuple[str, np.ndarray]]:
    """
    Generate several OCR-friendly versions.

    Important:
    We DO NOT rely on one aggressive binary image.
    """

    up = upscale(image, 2.5)

    g = gray(up)

    enhanced = clahe_enhance(up)

    denoised = gentle_denoise(enhanced)

    sharp = sharpen(denoised)

    variants = []

    # 1. Original grayscale
    variants.append(("gray", g))

    # 2. CLAHE
    variants.append(("clahe", enhanced))

    # 3. Denoised
    variants.append(("denoised", denoised))

    # 4. Sharpened
    variants.append(("sharp", sharp))

    # 5. OTSU
    _, otsu = cv2.threshold(
        sharp,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    variants.append(("otsu", otsu))

    # 6. Adaptive threshold
    adaptive = cv2.adaptiveThreshold(
        sharp,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        41,
        11,
    )

    variants.append(("adaptive", adaptive))

    # 7. Black-hat enhancement.
    # Useful when dark printed text appears on uneven bright packaging.
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (31, 31),
    )

    blackhat = cv2.morphologyEx(
        enhanced,
        cv2.MORPH_BLACKHAT,
        kernel,
    )

    blackhat = cv2.normalize(
        blackhat,
        None,
        0,
        255,
        cv2.NORM_MINMAX,
    )

    variants.append(("blackhat", blackhat))

    return variants


# ---------------------------------------------------------
# IMAGE CROPS
# ---------------------------------------------------------
def make_crops(image: np.ndarray) -> list[tuple[str, np.ndarray]]:
    """
    Create targeted OCR views.

    The bottom-right declaration panel on many packaged products
    can contain small and rotated text, so it gets dedicated crops.
    """

    h, w = image.shape[:2]

    crops = []

    # 1. Full image
    crops.append(("full", image))

    # 2. Left side
    crops.append(
        (
            "left",
            image[:, :int(w * 0.62)],
        )
    )

    # 3. Right side
    crops.append(
        (
            "right",
            image[:, int(w * 0.38):],
        )
    )

    # 4. Center
    crops.append(
        (
            "center",
            image[
                int(h * 0.08):int(h * 0.92),
                int(w * 0.08):int(w * 0.92),
            ],
        )
    )

    # 5. Bottom-right declaration area
    #
    # This is especially useful for:
    # MRP
    # Net Quantity
    # Unit Sale Price
    # Batch No.
    # Date
    #
    # These declarations are often printed in a small block.
    bottom_right = image[
        int(h * 0.55):h,
        int(w * 0.45):w,
    ]

    crops.append(
        ("bottom_right", bottom_right)
    )

    # 6. Bottom declaration area
    bottom = image[
        int(h * 0.65):h,
        int(w * 0.30):w,
    ]

    crops.append(
        ("bottom_declarations", bottom)
    )

    return crops







def make_rotated_variants(
    image: np.ndarray,
) -> list[tuple[str, np.ndarray]]:
    """
    Generate rotated versions for small/vertical declarations.
    """

    variants = []

    variants.append(("normal", image))

    variants.append(
        (
            "rot90",
            cv2.rotate(
                image,
                cv2.ROTATE_90_CLOCKWISE,
            ),
        )
    )

    variants.append(
        (
            "rot270",
            cv2.rotate(
                image,
                cv2.ROTATE_90_COUNTERCLOCKWISE,
            ),
        )
    )

    return variants
# ---------------------------------------------------------
# OCR
# ---------------------------------------------------------

def safe_confidence(value) -> float:
    try:
        value = float(value)
    except Exception:
        return -1.0

    return value


def normalize_text(text: str) -> str:
    """
    Normalize text only for duplicate detection.

    We keep the original OCR text elsewhere.
    """

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9₹%./:@\- ]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def run_single_ocr(
    image: np.ndarray,
    psm: int,
) -> list[TextLine]:

    results: list[TextLine] = []

    configs = [
        f"--oem 3 --psm {psm}",
    ]

    for config in configs:

        data = pytesseract.image_to_data(
            image,
            lang=settings.OCR_LANGUAGES,
            output_type=Output.DICT,
            config=config,
        )

        lines_map: dict[tuple[int, int], list[dict]] = {}

        n = len(data["text"])

        for i in range(n):

            word = data["text"][i].strip()

            conf = safe_confidence(
                data["conf"][i]
            )

            if not word:
                continue

            if conf < 0:
                continue

            block = int(data["block_num"][i])
            line = int(data["line_num"][i])

            key = (block, line)

            lines_map.setdefault(
                key,
                [],
            ).append(
                {
                    "word": word,
                    "left": int(data["left"][i]),
                    "top": int(data["top"][i]),
                    "width": int(data["width"][i]),
                    "height": int(data["height"][i]),
                    "conf": conf,
                }
            )

        for (block_num, line_num), words in lines_map.items():

            if not words:
                continue

            text = " ".join(
                w["word"]
                for w in words
            ).strip()

            if not text:
                continue

            x0 = min(
                w["left"]
                for w in words
            )

            y0 = min(
                w["top"]
                for w in words
            )

            x1 = max(
                w["left"] + w["width"]
                for w in words
            )

            y1 = max(
                w["top"] + w["height"]
                for w in words
            )

            confidence = sum(
                w["conf"]
                for w in words
            ) / len(words)

            results.append(
                TextLine(
                    text=text,
                    x=x0,
                    y=y0,
                    width=x1 - x0,
                    height=y1 - y0,
                    confidence=round(
                        confidence,
                        1,
                    ),
                    block_num=block_num,
                    line_num=line_num,
                )
            )

    return results


# ---------------------------------------------------------
# IMPORTANT DECLARATION KEYWORDS
# ---------------------------------------------------------

IMPORTANT_TERMS = [
    "mrp",
    "maximum retail price",
    "net quantity",
    "net qty",
    "quantity",
    "manufactured by",
    "marketed by",
    "packed by",
    "imported by",
    "date",
    "month",
    "year",
    "mfg",
    "mfd",
    "batch",
    "lot",
    "unit sale price",
    "price",
    "consumer care",
    "customer care",
    "ingredients",
    "allergen",
    "fssai",
    "license",
    "lic",
    "contact",
    "address",
    "email",
    "phone",
]


def importance_score(text: str) -> float:
    normalized = normalize_text(text)

    score = 0.0

    for term in IMPORTANT_TERMS:
        if term in normalized:
            score += 25.0

    # Numbers are important for MRP, quantity, dates, phone numbers etc.
    if re.search(r"\d", text):
        score += 8.0

    # Currency / percentage / units
    if re.search(
        r"(₹|rs\.?|kg|g\b|gm|mg|ml|l\b|%|pcs)",
        normalized,
    ):
        score += 12.0

    return score


# ---------------------------------------------------------
# MERGE OCR RESULTS
# ---------------------------------------------------------

def merge_lines(
    candidates: list[TextLine],
) -> list[TextLine]:

    groups: dict[str, TextLine] = {}

    for line in candidates:

        text = line.text.strip()

        if len(text) < 2:
            continue

        normalized = normalize_text(text)

        if not normalized:
            continue

        score = (
            line.confidence
            + importance_score(text)
        )

        if normalized not in groups:

            groups[normalized] = line

        else:

            existing = groups[normalized]

            existing_score = (
                existing.confidence
                + importance_score(existing.text)
            )

            if score > existing_score:
                groups[normalized] = line

    result = list(groups.values())

    # Remove very weak garbage unless it looks like an important declaration.
    filtered = []

    for line in result:

        score = importance_score(line.text)

        if line.confidence >= 30:
            filtered.append(line)

        elif score >= 25:
            filtered.append(line)

    # Highest-quality first internally.
    filtered.sort(
        key=lambda x: (
            -importance_score(x.text),
            -x.confidence,
            x.y,
            x.x,
        )
    )

    return filtered


# ---------------------------------------------------------
# MAIN OCR
# ---------------------------------------------------------

def run_ocr(image_path: str) -> OcrResult:
    """
    OCR pipeline for packaged-commodity labels.

    Uses:
    - full image OCR
    - targeted declaration crops
    - rotated OCR for vertical declarations
    - grayscale / CLAHE / sharpened variants
    """

    original = load_image(image_path)

    h, w = original.shape[:2]

    # Keep very large photos manageable.
    MAX_SIDE = 1800

    longest_side = max(h, w)

    if longest_side > MAX_SIDE:
        scale = MAX_SIDE / float(longest_side)

        original = cv2.resize(
            original,
            (
                int(w * scale),
                int(h * scale),
            ),
            interpolation=cv2.INTER_AREA,
        )

    all_candidates: list[TextLine] = []
    ocr_pass_texts: list[str] = []

    # -----------------------------------------------------
    # 1. FULL IMAGE
    # -----------------------------------------------------

    full_variants = [
        ("gray", gray(original)),
        ("clahe", clahe_enhance(original)),
        ("sharp", sharpen(original)),
    ]

    for variant_name, variant in full_variants:

        for psm in (6, 11):

            try:
                candidates = run_single_ocr(
                    variant,
                    psm,
                )

                all_candidates.extend(candidates)

                pass_text = "\n".join(
                    line.text for line in candidates
                )

                if pass_text.strip():
                    ocr_pass_texts.append(pass_text)

            except Exception as exc:
                print(
                    f"Full OCR failed "
                    f"(variant={variant_name}, psm={psm}): {exc}"
                )

    # -----------------------------------------------------
    # 2. TARGETED DECLARATION CROPS
    # -----------------------------------------------------

    crops = make_crops(original)

    for crop_name, crop in crops:

        if crop_name not in {
            "bottom_right",
            "bottom_declarations",
        }:
            continue

               # Try normal + rotated versions.
        rotated_versions = make_rotated_variants(crop)

        for rotation_name, rotated in rotated_versions:

            # IMPORTANT: upscale small declaration areas
            rotated = upscale(rotated, 3.0)

            variants = [
                ("gray", gray(rotated)),
                ("clahe", clahe_enhance(rotated)),
                ("sharp", sharpen(rotated)),
            ]

            for variant_name, variant in variants:
                for psm in (6, 11):
                    try:
                        candidates = run_single_ocr(
                            variant,
                            psm,
                        )

                        all_candidates.extend(candidates)

                        pass_text = "\n".join(
                            line.text for line in candidates
                        )

                        if pass_text.strip():
                            ocr_pass_texts.append(pass_text)

                    except Exception as exc:
                        print(
                            f"Targeted OCR failed "
                            f"(crop={crop_name}, "
                            f"rotation={rotation_name}, "
                            f"variant={variant_name}, "
                            f"psm={psm}): {exc}"
                        )

    # -----------------------------------------------------
    # 3. MERGE RESULTS
    # -----------------------------------------------------

    merged = merge_lines(all_candidates)

    final_h, final_w = original.shape[:2]

    return OcrResult(
        full_text="\n\n".join(ocr_pass_texts),
        lines=merged,
        image_width_px=final_w,
        image_height_px=final_h,
        skew_angle_deg=0.0,
    )
    

# ---------------------------------------------------------
# FONT SIZE ANALYSIS
# ---------------------------------------------------------

def px_to_mm(
    height_px: int,
    calibration_mm_per_px: Optional[float],
) -> tuple[float, str]:

    if calibration_mm_per_px:

        return (
            round(
                height_px *
                calibration_mm_per_px,
                2,
            ),
            "calibrated",
        )

    mm_per_px = (
        MM_PER_INCH /
        ASSUMED_DPI_FALLBACK
    )

    return (
        round(
            height_px *
            mm_per_px,
            2,
        ),
        "estimated",
    )


def analyze_font_sizes(
    ocr_result: OcrResult,
    calibration_mm_per_px: Optional[float] = None,
) -> list[dict]:

    measurements = []

    for line in ocr_result.lines:

        height_mm, confidence = px_to_mm(
            line.height,
            calibration_mm_per_px,
        )

        measurements.append(
            {
                "text": line.text,
                "bbox": {
                    "x": line.x,
                    "y": line.y,
                    "width": line.width,
                    "height": line.height,
                },
                "ocr_confidence_pct": line.confidence,
                "estimated_height_mm": height_mm,
                "measurement_confidence": confidence,
            }
        )

    return measurements