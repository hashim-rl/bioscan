"""
BioScan Digital Image Processing (DIP) Pipeline
Handles Region of Interest (ROI) cropping, normalization, CLAHE contrast enhancement,
noise reduction, edge sharpening, image quality assessment, and Base64 conversion.
"""

import base64
import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional

from app.utils.constants import (
    ROI_WIDTH,
    ROI_HEIGHT,
    BLUR_THRESHOLD,
    MIN_BRIGHTNESS,
    MAX_BRIGHTNESS,
    GUIDE_CONFIG,
    BIOMETRIC_LEFT_FINGERS,
)


def crop_roi_by_category(frame: np.ndarray, category: str) -> np.ndarray:
    """
    Crops the Region of Interest (ROI) from the camera frame using the EXACT same
    normalized relative coordinates that are presented on screen by the positioning guide.
    This guarantees 100% consistency between Registration and Verification captures.

    Args:
        frame: Input BGR/Grayscale image array.
        category: Biometric category identifier (e.g. LEFT_FINGERS, LEFT_THUMB).

    Returns:
        Cropped numpy array of the target region.
    """
    h, w = frame.shape[:2]
    cfg = GUIDE_CONFIG.get(category, GUIDE_CONFIG[BIOMETRIC_LEFT_FINGERS])
    w_ratio = cfg["width_ratio"]
    h_ratio = cfg["height_ratio"]

    box_w = int(w * w_ratio)
    box_h = int(h * h_ratio)
    box_x = max(0, (w - box_w) // 2)
    box_y = max(0, (h - box_h) // 2)

    # Bounding box slice [y: y + h, x: x + w]
    cropped = frame[box_y : box_y + box_h, box_x : box_x + box_w]

    if cropped.size == 0:
        return frame.copy()

    return cropped


def check_image_quality(image: np.ndarray) -> Dict[str, Any]:
    """
    Evaluates image quality metrics to reject severely degraded captures.
    Checks:
    1. Sharpness / Blur: Laplacian variance (higher = sharper).
    2. Illumination: Mean pixel intensity (checks too dark or overexposed).

    Returns:
        dict: {
            "passed": bool,
            "reason": str,
            "blur_score": float,
            "mean_brightness": float
        }
    """
    if image is None or image.size == 0:
        return {
            "passed": False,
            "reason": "Invalid or empty image frame.",
            "blur_score": 0.0,
            "mean_brightness": 0.0,
        }

    # Ensure single channel grayscale for variance and brightness
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # 1. Blur evaluation using Laplacian operator variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = float(laplacian.var())

    # 2. Illumination evaluation
    mean_brightness = float(np.mean(gray))

    # Evaluate against thresholds: Check illumination first, then blur
    if mean_brightness < MIN_BRIGHTNESS:
        return {
            "passed": False,
            "reason": f"Image is too dark ({mean_brightness:.1f} < {MIN_BRIGHTNESS:.1f}). Increase lighting.",
            "blur_score": blur_score,
            "mean_brightness": mean_brightness,
        }

    if mean_brightness > MAX_BRIGHTNESS:
        return {
            "passed": False,
            "reason": f"Image is too bright ({mean_brightness:.1f} > {MAX_BRIGHTNESS:.1f}). Reduce glare.",
            "blur_score": blur_score,
            "mean_brightness": mean_brightness,
        }

    if blur_score < BLUR_THRESHOLD:
        return {
            "passed": False,
            "reason": f"Image is blurry ({blur_score:.1f} < {BLUR_THRESHOLD:.1f}). Hold phone steady.",
            "blur_score": blur_score,
            "mean_brightness": mean_brightness,
        }

    return {
        "passed": True,
        "reason": "Quality acceptable.",
        "blur_score": blur_score,
        "mean_brightness": mean_brightness,
    }


def preprocess_image(
    raw_frame: np.ndarray,
    category: str,
    target_size: Tuple[int, int] = (ROI_WIDTH, ROI_HEIGHT),
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Executes the complete Digital Image Processing (DIP) enhancement pipeline.

    Stages:
    1. ROI extraction using identical category guide bounds.
    2. Scaling to uniform target resolution.
    3. Conversion to 8-bit grayscale.
    4. Quality check (blur and illumination).
    5. CLAHE (Contrast-Limited Adaptive Histogram Equalization) for localized contrast.
    6. Edge-preserving smoothing (Bilateral Filter) to suppress sensor noise while preserving ridge edges.
    7. Unsharp masking to sharpen crease/ridge contours.
    8. Intensity normalization.

    Args:
        raw_frame: Camera captured frame (BGR uint8).
        category: Biometric category identifier.
        target_size: (width, height) resolution for normalized template.

    Returns:
        (cropped_bgr, enhanced_grayscale, quality_dict)
    """
    if raw_frame is None or raw_frame.size == 0:
        raise ValueError("Cannot preprocess empty or None image frame.")

    # 1. Crop to ROI
    roi_bgr = crop_roi_by_category(raw_frame, category)

    # 2. Resize to standard dimensions
    resized_bgr = cv2.resize(roi_bgr, target_size, interpolation=cv2.INTER_AREA)

    # 3. Convert to Grayscale
    if len(resized_bgr.shape) == 3:
        gray = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2GRAY)
    else:
        gray = resized_bgr.copy()

    # 4. Check image quality
    quality = check_image_quality(gray)

    # 5. Contrast-Limited Adaptive Histogram Equalization (CLAHE)
    # Improves local ridge visibility without blowing out highlights or noise
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    clahe_enhanced = clahe.apply(gray)

    # 6. Noise reduction using Bilateral Filter
    # Bilateral filtering smooths skin texture noise while preserving high-gradient finger ridge edges
    denoised = cv2.bilateralFilter(clahe_enhanced, d=5, sigmaColor=50, sigmaSpace=50)

    # 7. Unsharp Masking for ridge sharpening
    # Formula: sharpened = original + weight * (original - gaussian_blurred)
    blurred = cv2.GaussianBlur(denoised, (0, 0), sigmaX=3.0)
    sharpened = cv2.addWeighted(denoised, 1.5, blurred, -0.5, 0)

    # 8. Final normalization to full 0-255 dynamic range
    normalized = cv2.normalize(sharpened, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    return resized_bgr, normalized, quality


def image_to_base64(image: np.ndarray, ext: str = ".png") -> str:
    """
    Encodes an OpenCV image array to compressed image bytes and then to a Base64 string.
    Base64 is strictly for clean offline SQLite persistence and display interchange.
    """
    if image is None or image.size == 0:
        raise ValueError("Cannot encode empty image.")

    success, buffer = cv2.imencode(ext, image)
    if not success:
        raise RuntimeError(f"Failed to encode image to {ext} format.")

    b64_bytes = base64.b64encode(buffer)
    return b64_bytes.decode("utf-8")


def base64_to_image(b64_string: str) -> np.ndarray:
    """
    Decodes a Base64 string back to an OpenCV image array (grayscale or BGR).
    Provides fully reversible reconstruction of stored enhanced templates.
    """
    if not b64_string:
        raise ValueError("Base64 string is empty.")

    # Strip potential data URL prefix if present
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]

    img_bytes = base64.b64decode(b64_string)
    np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)

    if image is None:
        raise ValueError("Could not decode image from provided Base64 data.")

    return image
