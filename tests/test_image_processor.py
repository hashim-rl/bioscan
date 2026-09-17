"""
Unit tests for Milestone 4 (DIP Pipeline) & Milestone 5 (Base64 Encoding).
"""

import os
import sys
import cv2
import numpy as np
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.image_processor import (
    crop_roi_by_category,
    check_image_quality,
    preprocess_image,
    image_to_base64,
    base64_to_image,
)
from app.utils.constants import (
    BIOMETRIC_LEFT_FINGERS,
    BIOMETRIC_LEFT_THUMB,
    ROI_WIDTH,
    ROI_HEIGHT,
    BLUR_THRESHOLD,
)


class TestImageProcessor(unittest.TestCase):
    def setUp(self):
        # Generate a synthetic sharp textured image
        self.height, self.width = 480, 640
        self.synthetic_frame = np.full((self.height, self.width, 3), 200, dtype=np.uint8)

        # Draw concentric rings / edges to emulate ridges
        center = (self.width // 2, self.height // 2)
        for r in range(15, 180, 10):
            cv2.circle(self.synthetic_frame, center, r, (40, 40, 40), 2)

    def test_crop_roi_consistency(self):
        """Verify cropping produces non-empty crops with expected proportions."""
        crop_fingers = crop_roi_by_category(self.synthetic_frame, BIOMETRIC_LEFT_FINGERS)
        crop_thumb = crop_roi_by_category(self.synthetic_frame, BIOMETRIC_LEFT_THUMB)

        self.assertGreater(crop_fingers.shape[1], crop_thumb.shape[1], "4-finger guide should be wider than thumb guide")
        self.assertGreater(crop_fingers.size, 0)
        self.assertGreater(crop_thumb.size, 0)

    def test_quality_check_sharp_vs_blurry(self):
        """Verify Laplacian blur detection."""
        # Sharp image should pass
        quality_sharp = check_image_quality(self.synthetic_frame)
        self.assertTrue(quality_sharp["passed"])
        self.assertGreater(quality_sharp["blur_score"], BLUR_THRESHOLD)

        # Blurring with heavy Gaussian kernel should fail
        blurred = cv2.GaussianBlur(self.synthetic_frame, (45, 45), 0)
        quality_blur = check_image_quality(blurred)
        self.assertFalse(quality_blur["passed"])
        self.assertLess(quality_blur["blur_score"], BLUR_THRESHOLD)
        self.assertIn("blurry", quality_blur["reason"].lower())

    def test_quality_check_brightness(self):
        """Verify dark and overexposed images are flagged."""
        # Pitch black image
        black_img = np.zeros((100, 100, 3), dtype=np.uint8)
        q_dark = check_image_quality(black_img)
        self.assertFalse(q_dark["passed"])
        self.assertIn("dark", q_dark["reason"].lower())

        # Overexposed image
        white_img = np.full((100, 100, 3), 250, dtype=np.uint8)
        q_bright = check_image_quality(white_img)
        self.assertFalse(q_bright["passed"])
        self.assertIn("bright", q_bright["reason"].lower())

    def test_full_dip_preprocessing_pipeline(self):
        """Verify end-to-end preprocessing produces normalized output."""
        roi_bgr, enhanced, quality = preprocess_image(
            self.synthetic_frame,
            BIOMETRIC_LEFT_THUMB,
            target_size=(ROI_WIDTH, ROI_HEIGHT),
        )

        # Dimensions must match target dimensions
        self.assertEqual(enhanced.shape, (ROI_HEIGHT, ROI_WIDTH))
        self.assertEqual(enhanced.dtype, np.uint8)
        # Enhanced image is single-channel grayscale
        self.assertEqual(len(enhanced.shape), 2)
        self.assertTrue(quality["passed"])

    def test_base64_roundtrip_reconstruction(self):
        """Verify image -> Base64 -> image round-trip preserves image perfectly."""
        _, enhanced, _ = preprocess_image(self.synthetic_frame, BIOMETRIC_LEFT_THUMB)

        # Encode to Base64
        b64_str = image_to_base64(enhanced, ext=".png")
        self.assertIsInstance(b64_str, str)
        self.assertGreater(len(b64_str), 100)

        # Decode back to numpy array
        reconstructed = base64_to_image(b64_str)
        self.assertEqual(reconstructed.shape, enhanced.shape)
        # For PNG (lossless), array contents must match exactly
        diff = np.max(np.abs(enhanced.astype(int) - reconstructed.astype(int)))
        self.assertEqual(diff, 0, "Lossless PNG Base64 roundtrip must have 0 pixel difference")


if __name__ == "__main__":
    unittest.main(verbosity=2)
