"""
Test suite to verify Milestone 1: Project Shell & Screen Instantiation.
"""

import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import BioScanApp


def test_milestone1_screens_load():
    """Verify all screens initialize without error and screen manager has them."""
    app = BioScanApp()
    sm = app.build()

    screen_names = [s.name for s in sm.screens]
    expected_screens = ["home", "register", "camera_capture", "verify", "result", "users"]

    print("Registered screens in ScreenManager:", screen_names)
    for s in expected_screens:
        assert s in screen_names, f"Screen '{s}' was not found in ScreenManager!"

    # Test transitions
    sm.current = "register"
    assert sm.current == "register"

    sm.current = "verify"
    assert sm.current == "verify"

    sm.current = "result"
    assert sm.current == "result"

    sm.current = "users"
    assert sm.current == "users"

    sm.current = "home"
    assert sm.current == "home"

    print("Milestone 1 Screen instantiation and transition tests passed successfully!")


if __name__ == "__main__":
    test_milestone1_screens_load()
