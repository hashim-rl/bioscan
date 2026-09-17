"""
Comprehensive Integration & Test Suite for BioScan.
Implements and automates all 10 Test Cases required by the specification:
TEST 1: Register new user with Left Thumb only.
TEST 2: Verify same Left Thumb (Expected: REGISTERED).
TEST 3: Scan an unregistered thumb (Expected: NOT REGISTERED).
TEST 4: Register one user with all four biometric categories.
TEST 5: Attempt to register same biometric category twice (Expected: Blocked).
TEST 6: Register two different users, verify each.
TEST 7: Try verifying a category with no records (Expected: Friendly message, no crash).
TEST 8: Capture intentionally blurry image (Expected: Quality check flags it).
TEST 9: Close/reopen database session (Expected: Data persists).
TEST 10: Delete user (Expected: Cascades and deletes all child biometrics).
"""

import os
import sys
import tempfile
import cv2
import numpy as np
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database import (
    init_database,
    create_user,
    get_user,
    get_all_users,
    save_biometric,
    get_biometrics_for_user,
    biometric_exists,
    delete_user,
    count_users,
    count_biometrics,
)
from app.services.image_processor import (
    preprocess_image,
    check_image_quality,
    image_to_base64,
    base64_to_image,
)
from app.services.recognition import (
    extract_features,
    serialize_descriptors,
    deserialize_descriptors,
    compare_descriptors,
    verify_against_templates,
)
from app.utils.constants import (
    BIOMETRIC_LEFT_FINGERS,
    BIOMETRIC_LEFT_THUMB,
    BIOMETRIC_RIGHT_FINGERS,
    BIOMETRIC_RIGHT_THUMB,
    BIOMETRIC_CATEGORIES,
    DEFAULT_MATCH_THRESHOLD,
)


def generate_biometric_pattern(pattern_id: int, noise_level: float = 0.0, angle: float = 0.0) -> np.ndarray:
    """
    Generates synthetic biometric images mimicking finger ridge arches and whorls.
    Supports introducing realistic variations (slight rotation, noise, translations).
    """
    h, w = 480, 640
    img = np.full((h, w, 3), 220, dtype=np.uint8)

    cx, cy = w // 2, h // 2
    if pattern_id == 1:
        # Concentric elliptical whorls
        for r in range(25, 200, 10):
            cv2.ellipse(img, (cx, cy), (r, int(r * 1.35)), angle, 0, 360, (50, 50, 50), 2)
    elif pattern_id == 2:
        # Loop pattern with angled focal center
        for r in range(20, 190, 9):
            cv2.ellipse(img, (cx + 30, cy - 20), (r, int(r * 1.5)), 45 + angle, 0, 360, (40, 40, 40), 2)
    elif pattern_id == 3:
        # Parallel ridge arches
        for y in range(80, 400, 14):
            pts = np.array([[x, int(y - 30 * np.sin(x / 80.0))] for x in range(100, 540)], np.int32)
            cv2.polylines(img, [pts], False, (45, 45, 45), 2)
    else:
        # Cross-hatch composite
        for x in range(100, 540, 20):
            cv2.line(img, (x, 100), (x, 400), (50, 50, 50), 2)
        for y in range(100, 400, 20):
            cv2.line(img, (100, y), (540, y), (50, 50, 50), 2)

    # Add Gaussian noise if specified
    if noise_level > 0.0:
        noise = np.random.normal(0, noise_level, img.shape).astype(np.int16)
        noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return noisy

    return img


class TestBioScanFullWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        init_database(self.temp_db_path)

    def tearDown(self):
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except PermissionError:
                pass

    def test_01_and_02_register_and_verify_left_thumb(self):
        """TEST 1 & 2: Register user with Left Thumb only, then verify same Left Thumb."""
        # 1. Acquire raw frame & execute DIP pipeline
        raw_capture = generate_biometric_pattern(pattern_id=1)
        _, enhanced, quality = preprocess_image(raw_capture, BIOMETRIC_LEFT_THUMB)
        self.assertTrue(quality["passed"])

        # 2. Extract features & serialize to Base64 and BLOB
        b64_str = image_to_base64(enhanced)
        kps, desc = extract_features(enhanced)
        self.assertIsNotNone(desc)
        feat_bytes = serialize_descriptors(desc)

        # 3. Persist in SQLite
        created = create_user("U-001", "Tariq", db_path=self.temp_db_path)
        self.assertTrue(created)
        saved = save_biometric("U-001", BIOMETRIC_LEFT_THUMB, b64_str, feat_bytes, db_path=self.temp_db_path)
        self.assertTrue(saved)

        # 4. Verify same biometric (with slight realistic camera noise & slight 3 deg rotation)
        live_scan = generate_biometric_pattern(pattern_id=1, noise_level=5.0, angle=3.0)
        _, live_enhanced, _ = preprocess_image(live_scan, BIOMETRIC_LEFT_THUMB)
        _, live_desc = extract_features(live_enhanced)

        res = verify_against_templates(
            query_descriptors=live_desc,
            category=BIOMETRIC_LEFT_THUMB,
            db_path=self.temp_db_path,
            threshold=DEFAULT_MATCH_THRESHOLD,
        )

        self.assertTrue(res["matched"], f"Verification failed. Score: {res['best_score']}")
        self.assertEqual(res["user_id"], "U-001")
        self.assertEqual(res["name"], "Tariq")
        self.assertGreaterEqual(res["best_score"], DEFAULT_MATCH_THRESHOLD)

    def test_03_unregistered_thumb_returns_not_registered(self):
        """TEST 3: Scan an unregistered thumb -> NOT REGISTERED."""
        # Register user with pattern 1
        raw1 = generate_biometric_pattern(pattern_id=1)
        _, enh1, _ = preprocess_image(raw1, BIOMETRIC_LEFT_THUMB)
        _, desc1 = extract_features(enh1)
        create_user("U-001", "Tariq", db_path=self.temp_db_path)
        save_biometric("U-001", BIOMETRIC_LEFT_THUMB, image_to_base64(enh1), serialize_descriptors(desc1), db_path=self.temp_db_path)

        # Scan unregistered thumb (pattern 2)
        raw_unregistered = generate_biometric_pattern(pattern_id=2)
        _, enh_unreg, _ = preprocess_image(raw_unregistered, BIOMETRIC_LEFT_THUMB)
        _, desc_unreg = extract_features(enh_unreg)

        res = verify_against_templates(
            query_descriptors=desc_unreg,
            category=BIOMETRIC_LEFT_THUMB,
            db_path=self.temp_db_path,
            threshold=DEFAULT_MATCH_THRESHOLD,
        )
        self.assertFalse(res["matched"], "Unregistered thumb should NOT match")
        self.assertEqual(res["user_id"], "")

    def test_04_register_all_four_categories(self):
        """TEST 4: Register one user with all four biometric categories."""
        create_user("U-FULL", "Fatima", db_path=self.temp_db_path)

        for idx, cat in enumerate(BIOMETRIC_CATEGORIES, start=1):
            raw = generate_biometric_pattern(pattern_id=idx % 3 + 1)
            _, enh, q = preprocess_image(raw, cat)
            _, desc = extract_features(enh)
            saved = save_biometric(
                "U-FULL",
                cat,
                image_to_base64(enh),
                serialize_descriptors(desc),
                db_path=self.temp_db_path,
            )
            self.assertTrue(saved)

        bios = get_biometrics_for_user("U-FULL", db_path=self.temp_db_path)
        self.assertEqual(len(bios), 4)

    def test_05_prevent_duplicate_category(self):
        """TEST 5: Attempt to register same biometric category twice -> Blocked."""
        create_user("U-DUP", "Zayd", db_path=self.temp_db_path)
        dummy_feat = b"\x01" * 32

        # First registration of Right Thumb
        ok1 = save_biometric("U-DUP", BIOMETRIC_RIGHT_THUMB, "b64", dummy_feat, db_path=self.temp_db_path)
        self.assertTrue(ok1)

        # Second registration of Right Thumb for same user
        ok2 = save_biometric("U-DUP", BIOMETRIC_RIGHT_THUMB, "b64_new", dummy_feat, db_path=self.temp_db_path)
        self.assertFalse(ok2, "Duplicate category for the same user must be blocked")

    def test_06_two_different_users_verified_separately(self):
        """TEST 6: Register two different users, verify each matches only their own record."""
        # User 1: pattern 1
        raw1 = generate_biometric_pattern(pattern_id=1)
        _, enh1, _ = preprocess_image(raw1, BIOMETRIC_LEFT_THUMB)
        _, desc1 = extract_features(enh1)
        create_user("U-USER1", "User One", db_path=self.temp_db_path)
        save_biometric("U-USER1", BIOMETRIC_LEFT_THUMB, "b64", serialize_descriptors(desc1), db_path=self.temp_db_path)

        # User 2: pattern 3
        raw2 = generate_biometric_pattern(pattern_id=3)
        _, enh2, _ = preprocess_image(raw2, BIOMETRIC_LEFT_THUMB)
        _, desc2 = extract_features(enh2)
        create_user("U-USER2", "User Two", db_path=self.temp_db_path)
        save_biometric("U-USER2", BIOMETRIC_LEFT_THUMB, "b64", serialize_descriptors(desc2), db_path=self.temp_db_path)

        # Verify User 1
        res1 = verify_against_templates(desc1, BIOMETRIC_LEFT_THUMB, db_path=self.temp_db_path)
        self.assertTrue(res1["matched"])
        self.assertEqual(res1["user_id"], "U-USER1")

        # Verify User 2
        res2 = verify_against_templates(desc2, BIOMETRIC_LEFT_THUMB, db_path=self.temp_db_path)
        self.assertTrue(res2["matched"])
        self.assertEqual(res2["user_id"], "U-USER2")

    def test_07_verify_category_with_no_records(self):
        """TEST 7: Verify a category when database has no records for that category."""
        # Database is completely empty or has other categories
        raw = generate_biometric_pattern(pattern_id=1)
        _, enh, _ = preprocess_image(raw, BIOMETRIC_RIGHT_FINGERS)
        _, desc = extract_features(enh)

        res = verify_against_templates(desc, BIOMETRIC_RIGHT_FINGERS, db_path=self.temp_db_path)
        self.assertFalse(res["matched"])
        self.assertEqual(res["candidate_count"], 0)
        self.assertIn("no registered templates", res["status_message"].lower())

    def test_08_blurry_image_quality_rejection(self):
        """TEST 8: Capture intentionally blurry image -> detected by quality check."""
        raw = generate_biometric_pattern(pattern_id=1)
        blurry = cv2.GaussianBlur(raw, (51, 51), 0)

        quality = check_image_quality(blurry)
        self.assertFalse(quality["passed"])
        self.assertIn("blurry", quality["reason"].lower())

    def test_09_database_persistence_across_sessions(self):
        """TEST 9: Close and reopen database -> records persist."""
        create_user("U-PERSIST", "Permanent User", db_path=self.temp_db_path)
        save_biometric("U-PERSIST", BIOMETRIC_LEFT_FINGERS, "b64", b"\x00" * 32, db_path=self.temp_db_path)

        # Re-initialize / reconnect
        user = get_user("U-PERSIST", db_path=self.temp_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Permanent User")
        self.assertTrue(biometric_exists("U-PERSIST", BIOMETRIC_LEFT_FINGERS, db_path=self.temp_db_path))

    def test_10_delete_user_and_biometrics(self):
        """TEST 10: Delete user -> user and associated biometric records removed."""
        create_user("U-REMOVE", "Temp Delete", db_path=self.temp_db_path)
        save_biometric("U-REMOVE", BIOMETRIC_LEFT_THUMB, "b64", b"\x00" * 32, db_path=self.temp_db_path)
        save_biometric("U-REMOVE", BIOMETRIC_RIGHT_THUMB, "b64", b"\x00" * 32, db_path=self.temp_db_path)

        self.assertEqual(count_users(db_path=self.temp_db_path), 1)
        self.assertEqual(count_biometrics(db_path=self.temp_db_path), 2)

        # Delete
        success = delete_user("U-REMOVE", db_path=self.temp_db_path)
        self.assertTrue(success)

        # Verify removal
        self.assertIsNone(get_user("U-REMOVE", db_path=self.temp_db_path))
        self.assertEqual(count_users(db_path=self.temp_db_path), 0)
        self.assertEqual(count_biometrics(db_path=self.temp_db_path), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
