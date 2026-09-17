"""
Unit tests for Milestone 2: SQLite Database Service.
Tests CRUD operations, uniqueness constraints, and foreign key cascade deletion.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database import (
    init_database,
    create_user,
    get_user,
    get_all_users,
    save_biometric,
    get_biometrics_for_user,
    get_biometrics_by_type,
    biometric_exists,
    delete_user,
    count_users,
    count_biometrics,
    get_connection,
)
from app.utils.constants import (
    BIOMETRIC_LEFT_FINGERS,
    BIOMETRIC_LEFT_THUMB,
    BIOMETRIC_RIGHT_FINGERS,
    BIOMETRIC_RIGHT_THUMB,
)


class TestDatabaseService(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file for each test
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)  # Close immediately so Windows permits sqlite connection
        init_database(self.temp_db_path)

    def tearDown(self):
        # Clean up temporary database
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except PermissionError:
                pass

    def test_foreign_keys_pragma_enabled(self):
        """Ensure foreign keys PRAGMA is active on connections."""
        conn = get_connection(self.temp_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys;")
            fk_status = cursor.fetchone()[0]
            self.assertEqual(fk_status, 1, "PRAGMA foreign_keys must be ON (1)")
        finally:
            conn.close()

    def test_create_and_retrieve_user(self):
        """Test creating and retrieving a user."""
        res = create_user("U-101", "Alice Smith", db_path=self.temp_db_path)
        self.assertTrue(res)

        user = get_user("U-101", db_path=self.temp_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["user_id"], "U-101")
        self.assertEqual(user["name"], "Alice Smith")

        # Duplicate user_id must fail
        dup = create_user("U-101", "Alice Duplicate", db_path=self.temp_db_path)
        self.assertFalse(dup)

    def test_save_and_retrieve_biometrics(self):
        """Test saving biometrics and retrieving them for a user."""
        create_user("U-102", "Bob Johnson", db_path=self.temp_db_path)

        dummy_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA"
        dummy_feat = b"\x00\x01\x02\x03" * 8  # 32 bytes

        # Save Left Thumb
        saved = save_biometric("U-102", BIOMETRIC_LEFT_THUMB, dummy_b64, dummy_feat, db_path=self.temp_db_path)
        self.assertTrue(saved)
        self.assertTrue(biometric_exists("U-102", BIOMETRIC_LEFT_THUMB, db_path=self.temp_db_path))

        # Save Right Fingers
        saved2 = save_biometric("U-102", BIOMETRIC_RIGHT_FINGERS, dummy_b64, dummy_feat, db_path=self.temp_db_path)
        self.assertTrue(saved2)

        # Duplicate same category for same user must be blocked
        dup_bio = save_biometric("U-102", BIOMETRIC_LEFT_THUMB, dummy_b64, dummy_feat, db_path=self.temp_db_path)
        self.assertFalse(dup_bio, "Duplicate category for same user must return False")

        # Retrieve for user
        user_bios = get_biometrics_for_user("U-102", db_path=self.temp_db_path)
        self.assertEqual(len(user_bios), 2)

    def test_get_biometrics_by_type(self):
        """Test filtering biometrics by category across multiple users."""
        create_user("U-A", "User A", db_path=self.temp_db_path)
        create_user("U-B", "User B", db_path=self.temp_db_path)

        dummy_b64 = "base64placeholder"
        dummy_feat = b"\xaa\xbb" * 16

        save_biometric("U-A", BIOMETRIC_LEFT_THUMB, dummy_b64, dummy_feat, db_path=self.temp_db_path)
        save_biometric("U-B", BIOMETRIC_LEFT_THUMB, dummy_b64, dummy_feat, db_path=self.temp_db_path)
        save_biometric("U-A", BIOMETRIC_RIGHT_THUMB, dummy_b64, dummy_feat, db_path=self.temp_db_path)

        left_thumbs = get_biometrics_by_type(BIOMETRIC_LEFT_THUMB, db_path=self.temp_db_path)
        self.assertEqual(len(left_thumbs), 2)
        # Verify joined user name is included
        names = {item["name"] for item in left_thumbs}
        self.assertIn("User A", names)
        self.assertIn("User B", names)

    def test_delete_user_and_cascade_biometrics(self):
        """Ensure deleting a user cascades and removes all associated biometrics."""
        create_user("U-DELETE", "Temp User", db_path=self.temp_db_path)
        save_biometric("U-DELETE", BIOMETRIC_LEFT_FINGERS, "b64", b"feat", db_path=self.temp_db_path)
        save_biometric("U-DELETE", BIOMETRIC_RIGHT_FINGERS, "b64", b"feat", db_path=self.temp_db_path)

        self.assertEqual(count_biometrics(db_path=self.temp_db_path), 2)
        self.assertEqual(count_users(db_path=self.temp_db_path), 1)

        # Delete user
        deleted = delete_user("U-DELETE", db_path=self.temp_db_path)
        self.assertTrue(deleted)

        # Check user is gone
        self.assertIsNone(get_user("U-DELETE", db_path=self.temp_db_path))
        self.assertEqual(count_users(db_path=self.temp_db_path), 0)

        # Check all child biometrics were cascaded and deleted
        remaining_bios = get_biometrics_for_user("U-DELETE", db_path=self.temp_db_path)
        self.assertEqual(len(remaining_bios), 0)
        self.assertEqual(count_biometrics(db_path=self.temp_db_path), 0, "Biometrics should be deleted via cascade")


if __name__ == "__main__":
    unittest.main(verbosity=2)
