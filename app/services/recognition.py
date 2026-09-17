"""
BioScan Biometric Feature Extraction & Prototype Matching Service
Uses OpenCV ORB (Oriented FAST and Rotated BRIEF) feature extraction and BFMatcher.
Note: This is an academic camera-based biometric image matching prototype,
NOT a banking-grade fingerprint authentication engine.
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional, Dict, Any

from app.utils.constants import (
    ORB_N_FEATURES,
    ORB_SCALE_FACTOR,
    ORB_N_LEVELS,
    HAMMING_GOOD_MATCH_MAX_DIST,
    DEFAULT_MATCH_THRESHOLD,
)
from app.services.database import get_biometrics_by_type


def get_orb_detector() -> cv2.ORB:
    """Creates and configures an ORB feature detector instance."""
    return cv2.ORB_create(
        nfeatures=ORB_N_FEATURES,
        scaleFactor=ORB_SCALE_FACTOR,
        nlevels=ORB_N_LEVELS,
        edgeThreshold=15,
        firstLevel=0,
        WTA_K=2,
        scoreType=cv2.ORB_HARRIS_SCORE,
        patchSize=31,
        fastThreshold=12,
    )


def extract_features(image: np.ndarray) -> Tuple[List[cv2.KeyPoint], Optional[np.ndarray]]:
    """
    Detects ORB keypoints and computes binary descriptors for an enhanced image.

    Args:
        image: Single-channel 8-bit grayscale image (DIP enhanced).

    Returns:
        (keypoints, descriptors): descriptors has shape (N, 32) uint8, or None if no features.
    """
    if image is None or image.size == 0:
        return [], None

    # Ensure grayscale 8-bit
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    detector = get_orb_detector()
    keypoints, descriptors = detector.detectAndCompute(gray, None)

    # Log feature extraction details for academic inspection and tuning
    kp_count = len(keypoints) if keypoints else 0
    desc_count = descriptors.shape[0] if (descriptors is not None and descriptors.size > 0) else 0
    print(f"[BioScan Recognition] Feature extraction: {kp_count} keypoints, {desc_count} descriptors.")

    if descriptors is None or descriptors.size == 0 or desc_count == 0:
        return keypoints, None

    return keypoints, descriptors.astype(np.uint8)


def serialize_descriptors(descriptors: Optional[np.ndarray]) -> bytes:
    """
    Reliably serializes ORB descriptors into raw bytes for SQLite BLOB storage.
    ORB descriptors are uint8 with 32 bytes per descriptor.

    Args:
        descriptors: numpy array of shape (N, 32), dtype=uint8, or None.

    Returns:
        bytes: Contiguous binary bytes, or empty b"" if no descriptors.
    """
    if descriptors is None or descriptors.size == 0:
        return b""

    # Validate shape and type
    if not isinstance(descriptors, np.ndarray):
        return b""

    # Ensure 2D with 32 columns
    if len(descriptors.shape) != 2 or descriptors.shape[1] != 32:
        print(f"[BioScan Recognition] Warning: Unexpected descriptor shape {descriptors.shape}")
        return b""

    # Ensure uint8 contiguous
    arr = np.ascontiguousarray(descriptors, dtype=np.uint8)
    return arr.tobytes()


def deserialize_descriptors(feature_bytes: bytes) -> Optional[np.ndarray]:
    """
    Reliably reconstructs ORB descriptors from stored SQLite BLOB bytes.
    Validates byte length (must be multiple of 32) and reshapes to (-1, 32).

    Args:
        feature_bytes: Binary bytes from SQLite database.

    Returns:
        np.ndarray with shape (N, 32), dtype=uint8, or None if empty/invalid.
    """
    if not feature_bytes or len(feature_bytes) == 0:
        return None

    # Each ORB descriptor is exactly 32 bytes (256 bits)
    if len(feature_bytes) % 32 != 0:
        print(f"[BioScan Recognition] Error: feature_bytes length ({len(feature_bytes)}) is not multiple of 32.")
        return None

    try:
        arr = np.frombuffer(feature_bytes, dtype=np.uint8)
        descriptors = arr.reshape((-1, 32))
        return descriptors
    except Exception as e:
        print(f"[BioScan Recognition] Deserialization error: {e}")
        return None


def compare_descriptors(
    query_desc: Optional[np.ndarray],
    template_desc: Optional[np.ndarray],
    max_hamming_dist: float = HAMMING_GOOD_MATCH_MAX_DIST,
) -> Dict[str, Any]:
    """
    Compares two sets of ORB descriptors using BFMatcher with Hamming distance.
    Computes a normalized prototype match score based on good descriptor matches.

    Args:
        query_desc: Descriptors from live verification scan (N, 32).
        template_desc: Descriptors from saved database registration (M, 32).
        max_hamming_dist: Distance cutoff below which a match is considered 'good'.

    Returns:
        dict: {
            "score": float (0.0 to 100.0),
            "good_matches": int,
            "total_matches": int,
            "query_count": int,
            "template_count": int
        }
    """
    result = {
        "score": 0.0,
        "good_matches": 0,
        "total_matches": 0,
        "query_count": 0,
        "template_count": 0,
    }

    if query_desc is None or template_desc is None:
        return result

    q_count = query_desc.shape[0] if len(query_desc.shape) == 2 else 0
    t_count = template_desc.shape[0] if len(template_desc.shape) == 2 else 0
    result["query_count"] = q_count
    result["template_count"] = t_count

    # Require at least minimum descriptors to perform matching
    if q_count < 5 or t_count < 5:
        print(f"[BioScan Match] Insufficient descriptors (query={q_count}, template={t_count})")
        return result

    # BFMatcher with Hamming distance and cross-check enabled for mutual nearest neighbors
    try:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        raw_matches = matcher.match(query_desc, template_desc)
    except Exception as e:
        print(f"[BioScan Match] Matcher exception: {e}")
        return result

    result["total_matches"] = len(raw_matches)

    # Filter matches by maximum Hamming distance threshold
    good_matches = [m for m in raw_matches if m.distance <= max_hamming_dist]
    num_good = len(good_matches)
    result["good_matches"] = num_good

    # Prototype Score formula:
    # Ratio of verified good matches relative to the smaller of the two descriptor sets,
    # expressed as a percentage [0.0 - 100.0].
    # Using the minimum set size accommodates differences in cropped ridge areas.
    base_count = min(q_count, t_count)
    score = (num_good / float(base_count)) * 100.0
    score = min(100.0, max(0.0, score))
    result["score"] = round(score, 2)

    print(
        f"[BioScan Match] Compared: query={q_count}, template={t_count} | "
        f"raw_matches={len(raw_matches)}, good_matches={num_good} | Score: {result['score']}%"
    )

    return result


def verify_against_templates(
    query_descriptors: Optional[np.ndarray],
    category: str,
    db_path: Optional[str] = None,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> Dict[str, Any]:
    """
    Matches live query descriptors against all database templates of the EXACT same biometric category.
    Cross-category comparison (e.g. Left Thumb vs Right Fingers) is strictly forbidden.

    Returns:
        dict: {
            "matched": bool,
            "best_score": float,
            "threshold": float,
            "user_id": str,
            "name": str,
            "candidate_count": int,
            "good_matches": int,
            "status_message": str
        }
    """
    output = {
        "matched": False,
        "best_score": 0.0,
        "threshold": threshold,
        "user_id": "",
        "name": "",
        "candidate_count": 0,
        "good_matches": 0,
        "status_message": "No matching biometric registration was found.",
    }

    if query_descriptors is None or query_descriptors.size == 0:
        output["status_message"] = "Could not extract sufficient features from capture."
        return output

    # Fetch templates restricted to this specific biometric category
    templates = get_biometrics_by_type(category, db_path=db_path)
    output["candidate_count"] = len(templates)

    if not templates:
        output["status_message"] = f"No registered templates found for category '{category}'."
        return output

    best_score = -1.0
    best_match_info = None

    for t in templates:
        t_desc = deserialize_descriptors(t["feature_data"])
        if t_desc is None:
            continue

        comp = compare_descriptors(query_descriptors, t_desc)
        score = comp["score"]

        if score > best_score:
            best_score = score
            best_match_info = {
                "user_id": t["user_id"],
                "name": t["name"],
                "good_matches": comp["good_matches"],
            }

    output["best_score"] = max(0.0, best_score)

    if best_match_info and best_score >= threshold:
        output["matched"] = True
        output["user_id"] = best_match_info["user_id"]
        output["name"] = best_match_info["name"]
        output["good_matches"] = best_match_info["good_matches"]
        output["status_message"] = "Biometric match verified against local registry."
    else:
        output["matched"] = False

    return output
