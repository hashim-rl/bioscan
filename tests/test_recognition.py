"""
Unit tests for Milestone 7: Feature Extraction & Matching Service.
"""

import os
import sys
import tempfile
import cv2
import numpy as np
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.recognition import (
    extract_features,
    serialize_descriptors,
    deserialize_descriptors,
    compare_descriptors,
    verify_against_templates,
)
from app.services.database import init_database, create_user, save_biometric
from app.utils.constants import (
    BIOMETRIC_LEFT_THUMB,
    BIOMETRIC_RIGHT_FINGERS,
    DEFAULT_MATCH_THRESHOLD,
)


class TestRecognition(unittest.TestCase):
    def setUp(self):
        # Generate synthetic patterns representing distinct biometric structures
        self.img1 = np.full((300, 300), 220, dtype=np.uint8)
        for r in range(20, 130, 8):
            cv2.ellipse(self.img1, (150, 150), (r, int(r * 1.3)), 25, 0, 360, 40, 2)

        # Pattern 2: completely different grid structure
        self.img2 = np.full((300, 300), 220, dtype=np.uint8)
        for x in range(20, 280, 20):
            cv2.line(self.img2, (x, 20), (x, 280), 40, 2)
        for y in range(20, 280, 20):
            cv2.line(self.img2, (20, y), (280, y), 40, 2)

    def test_feature_extraction_and_empty_handling(self):
        """Test feature extraction and robust handling of blank images."""
        kp1, desc1 = extract_features(self.img1)
        self.assertGreater(len(kp1), 20)
        self.assertIsNotNone(desc1)
        self.assertEqual(desc1.shape[1], 32)
        self.assertEqual(desc1.dtype, np.uint8)

        # Blank white image should not crash and may have None descriptors
        blank = np.full((200, 200), 255, dtype=np.uint8)
        kp_blank, desc_blank = extract_features(blank)
        self.assertIsNone(desc_blank)

    def test_descriptor_serialization_roundtrip(self):
        """Verify binary serialization and exact reconstruction of ORB descriptors."""
        _, desc = extract_features(self.img1)
        self.assertIsNotNone(desc)

        # Serialize
        serialized = serialize_descriptors(desc)
        self.assertIsInstance(serialized, bytes)
        self.assertEqual(len(serialized), desc.shape[0] * 32)

        # Deserialize
        recovered = deserialize_descriptors(serialized)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.shape, desc.shape)
        self.assertEqual(recovered.dtype, np.uint8)
        np.testing.assert_array_equal(desc, recovered)

        # Test edge cases: None, empty bytes, corrupt length
        self.assertEqual(serialize_descriptors(None), b"")
        self.assertIsNone(deserialize_descriptors(b""))
        self.assertIsNone(deserialize_descriptors(b"12345"))  # Not a multiple of 32

    def test_compare_descriptors_self_vs_different(self):
        """Verify matching score: identical images score high, different score low."""
        _, desc1 = extract_features(self.img1)
        _, desc2 = extract_features(self.img2)

        # Self match (identical images)
        comp_self = compare_descriptors(desc1, desc1)
        self.assertGreaterEqual(comp_self["score"], 80.0, "Identical image must score near 100%")

        # Match against completely different pattern
        comp_diff = compare_descriptors(desc1, desc2)
        self.assertLess(comp_diff["score"], comp_self["score"])
        self.assertLess(comp_diff["score"], 25.0)

    def test_verify_against_templates_with_sqlite(self):
        """Test verification search against SQLite database records."""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_database(db_path)
            create_user("U-TEST1", "Ahmed", db_path=db_path)

            _, desc1 = extract_features(self.img1)
            raw_bytes1 = serialize_descriptors(desc1)
            save_biometric("U-TEST1", BIOMETRIC_LEFT_THUMB, "b64_dummy", raw_bytes1, db_path=db_path)

            # Query with same pattern and same category -> MATCH
            res_match = verify_against_templates(
                query_descriptors=desc1,
                category=BIOMETRIC_LEFT_THUMB,
                db_path=db_path,
                threshold=DEFAULT_MATCH_THRESHOLD,
            )
            self.assertTrue(res_match["matched"])
            self.assertEqual(res_match["user_id"], "U-TEST1")
            self.assertEqual(res_match["name"], "Ahmed")

            # Query with same pattern but DIFFERENT category -> NO CANDIDATES
            res_wrong_cat = verify_against_templates(
                query_descriptors=desc1,
                category=BIOMETRIC_RIGHT_FINGERS,
                db_path=db_path,
                threshold=DEFAULT_MATCH_THRESHOLD,
            )
            self.assertFalse(res_wrong_cat["matched"])
            self.assertEqual(res_wrong_cat["candidate_count"], 0)

            # Query with DIFFERENT pattern -> NOT REGISTERED
            _, desc2 = extract_features(self.img2)
            res_no_match = verify_against_templates(
                query_descriptors=desc2,
                category=BIOMETRIC_LEFT_THUMB,
                db_path=db_path,
                threshold=DEFAULT_MATCH_THRESHOLD,
            )
            self.assertFalse(res_no_match["matched"])
        finally:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
