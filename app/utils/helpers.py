"""
BioScan Platform and Utility Helpers
Handles platform-specific storage directories, Android permissions,
and isolated camera frame orientation/rotation adjustment.
"""

import os
import sys
import cv2
import numpy as np
from kivy.utils import platform
from kivy.app import App


def is_android() -> bool:
    """Returns True if the app is currently running on Android."""
    return platform == "android"


def get_app_storage_dir() -> str:
    """
    Returns the app-private internal storage directory.
    - On Android: /data/data/org.bioscan.app/files (via user_data_dir)
    - On Desktop: App user data directory or local data/ fallback
    This avoids requiring broad storage permissions.
    """
    app = App.get_running_app()
    if app and hasattr(app, "user_data_dir") and app.user_data_dir:
        storage_dir = app.user_data_dir
    else:
        # Fallback for standalone tests or early initialization
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        storage_dir = os.path.join(base_dir, "data")

    os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def get_database_path() -> str:
    """Returns the absolute path to the local SQLite database file."""
    return os.path.join(get_app_storage_dir(), "bioscan.db")


def request_android_camera_permission(callback=None):
    """
    Requests CAMERA permission on Android at runtime.
    On non-Android platforms, immediately executes the callback with True.
    """
    if is_android():
        try:
            from android.permissions import request_permissions, Permission, check_permission

            has_camera = check_permission(Permission.CAMERA)
            if has_camera:
                if callback:
                    callback(True)
                return

            def on_permissions_result(permissions, grants):
                all_granted = all(grants)
                if callback:
                    callback(all_granted)

            request_permissions([Permission.CAMERA], on_permissions_result)
        except Exception as e:
            print(f"[BioScan Permissions] Android permission request failed: {e}")
            if callback:
                callback(False)
    else:
        # Desktop development environment
        if callback:
            callback(True)


def adjust_camera_orientation(
    frame: np.ndarray,
    rotation_code: int = None,
    mirror_horizontal: bool = False,
    mirror_vertical: bool = False
) -> np.ndarray:
    """
    Isolated camera orientation and mirroring transformation.
    Android sensors are typically mounted rotated 90 or 270 degrees in portrait.
    Keeping this isolated allows device-specific adjustments without touching the DIP pipeline.

    Args:
        frame: Raw input numpy BGR image from camera.
        rotation_code: None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, or cv2.ROTATE_90_COUNTERCLOCKWISE.
        mirror_horizontal: Flip horizontally (for selfie cameras if ever used).
        mirror_vertical: Flip vertically.

    Returns:
        Corrected orientation numpy array.
    """
    if frame is None or frame.size == 0:
        return frame

    result = frame.copy()

    # Apply rotation if specified
    if rotation_code is not None:
        result = cv2.rotate(result, rotation_code)

    # Apply horizontal flip if specified
    if mirror_horizontal:
        result = cv2.flip(result, 1)

    # Apply vertical flip if specified
    if mirror_vertical:
        result = cv2.flip(result, 0)

    return result
