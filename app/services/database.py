"""
BioScan SQLite Database Service
Provides local, offline persistence for registered users and biometric templates.
Enforces foreign keys (PRAGMA foreign_keys = ON) and uniqueness constraints.
Properly closes connections to avoid resource/file descriptor leaks.
"""

import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from app.utils.helpers import get_database_path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Opens an SQLite connection and explicitly enables foreign key support.
    PRAGMA foreign_keys = ON is required per connection in SQLite to ensure
    ON DELETE CASCADE automatically removes child biometrics when a user is deleted.
    """
    path = db_path or get_database_path()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session(db_path: Optional[str] = None):
    """Context manager ensuring transactions commit and connections cleanly close."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        yield cursor, conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(db_path: Optional[str] = None) -> None:
    """
    Initializes the local SQLite database schema.
    Creates 'users' and 'biometrics' tables with constraints.
    """
    with db_session(db_path) as (cursor, conn):
        # Users table: stores user identity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Biometrics table: stores Base64 image and serialized feature descriptors
        # UNIQUE(user_id, biometric_type) prevents duplicate biometric categories for a user
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS biometrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                biometric_type TEXT NOT NULL,
                image_base64 TEXT NOT NULL,
                feature_data BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, biometric_type)
            );
        """)

        # Indices for fast retrieval during verification and listing
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_biometrics_type ON biometrics(biometric_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_biometrics_user_type ON biometrics(user_id, biometric_type);")


def create_user(user_id: str, name: str, db_path: Optional[str] = None) -> bool:
    """
    Creates a new user record.
    Returns True if created, False if user_id already exists.
    """
    try:
        with db_session(db_path) as (cursor, conn):
            cursor.execute(
                "INSERT INTO users (user_id, name) VALUES (?, ?);",
                (user_id.strip(), name.strip())
            )
            return True
    except sqlite3.IntegrityError:
        # User ID already exists
        return False


def get_user(user_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single user record by user_id."""
    with db_session(db_path) as (cursor, conn):
        cursor.execute("SELECT * FROM users WHERE user_id = ?;", (user_id.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_users(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all registered users ordered by registration time."""
    with db_session(db_path) as (cursor, conn):
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC;")
        return [dict(row) for row in cursor.fetchall()]


def save_biometric(
    user_id: str,
    biometric_type: str,
    image_base64: str,
    feature_data: bytes,
    db_path: Optional[str] = None,
) -> bool:
    """
    Saves a biometric record for a user.
    Enforces uniqueness: cannot register the same biometric_type for the same user twice.
    Returns True on success, False if already registered or on error.
    """
    try:
        with db_session(db_path) as (cursor, conn):
            cursor.execute(
                """
                INSERT INTO biometrics (user_id, biometric_type, image_base64, feature_data)
                VALUES (?, ?, ?, ?);
                """,
                (user_id.strip(), biometric_type.strip(), image_base64, feature_data)
            )
            return True
    except sqlite3.IntegrityError as e:
        print(f"[BioScan DB] Biometric duplicate/integrity error: {e}")
        return False


def get_biometrics_for_user(user_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all registered biometric records for a specific user."""
    with db_session(db_path) as (cursor, conn):
        cursor.execute("SELECT * FROM biometrics WHERE user_id = ?;", (user_id.strip(),))
        return [dict(row) for row in cursor.fetchall()]


def get_biometrics_by_type(biometric_type: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all biometric records of a given category across all users.
    Joins with users table to provide user name along with template data.
    """
    with db_session(db_path) as (cursor, conn):
        cursor.execute(
            """
            SELECT b.id, b.user_id, u.name, b.biometric_type, b.image_base64, b.feature_data, b.created_at
            FROM biometrics b
            JOIN users u ON b.user_id = u.user_id
            WHERE b.biometric_type = ?;
            """,
            (biometric_type.strip(),)
        )
        return [dict(row) for row in cursor.fetchall()]


def biometric_exists(user_id: str, biometric_type: str, db_path: Optional[str] = None) -> bool:
    """Checks whether a specific biometric category is already registered for a user."""
    with db_session(db_path) as (cursor, conn):
        cursor.execute(
            "SELECT 1 FROM biometrics WHERE user_id = ? AND biometric_type = ?;",
            (user_id.strip(), biometric_type.strip())
        )
        return cursor.fetchone() is not None


def delete_user(user_id: str, db_path: Optional[str] = None) -> bool:
    """
    Deletes a user. Due to ON DELETE CASCADE with PRAGMA foreign_keys = ON,
    all biometrics belonging to this user are automatically and atomically deleted.
    """
    with db_session(db_path) as (cursor, conn):
        cursor.execute("DELETE FROM users WHERE user_id = ?;", (user_id.strip(),))
        return cursor.rowcount > 0


def count_users(db_path: Optional[str] = None) -> int:
    """Returns the total number of registered users."""
    with db_session(db_path) as (cursor, conn):
        cursor.execute("SELECT COUNT(*) FROM users;")
        return cursor.fetchone()[0]


def count_biometrics(db_path: Optional[str] = None) -> int:
    """Returns the total number of stored biometric templates."""
    with db_session(db_path) as (cursor, conn):
        cursor.execute("SELECT COUNT(*) FROM biometrics;")
        return cursor.fetchone()[0]
