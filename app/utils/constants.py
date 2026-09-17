"""
BioScan Application Constants
Defines biometric categories, default thresholds, color palettes, and UI metrics.
"""

# Biometric Category Identifiers
BIOMETRIC_LEFT_FINGERS = "LEFT_FINGERS"
BIOMETRIC_LEFT_THUMB = "LEFT_THUMB"
BIOMETRIC_RIGHT_FINGERS = "RIGHT_FINGERS"
BIOMETRIC_RIGHT_THUMB = "RIGHT_THUMB"

BIOMETRIC_CATEGORIES = [
    BIOMETRIC_LEFT_FINGERS,
    BIOMETRIC_LEFT_THUMB,
    BIOMETRIC_RIGHT_FINGERS,
    BIOMETRIC_RIGHT_THUMB,
]

# User-facing labels for biometric categories
BIOMETRIC_LABELS = {
    BIOMETRIC_LEFT_FINGERS: "Left Hand — 4 Fingers",
    BIOMETRIC_LEFT_THUMB: "Left Thumb",
    BIOMETRIC_RIGHT_FINGERS: "Right Hand — 4 Fingers",
    BIOMETRIC_RIGHT_THUMB: "Right Thumb",
}

# Positioning instructions per category
BIOMETRIC_INSTRUCTIONS = {
    BIOMETRIC_LEFT_FINGERS: "Place all 4 fingers (excluding thumb) inside the wide guide.",
    BIOMETRIC_LEFT_THUMB: "Place left thumb flat and centered inside the guide.",
    BIOMETRIC_RIGHT_FINGERS: "Place all 4 fingers (excluding thumb) inside the wide guide.",
    BIOMETRIC_RIGHT_THUMB: "Place right thumb flat and centered inside the guide.",
}

# Guide overlay aspect ratios and relative dimensions (relative to preview width/height)
# Four fingers: wide rectangular box
# Thumb: taller, centered compact box
GUIDE_CONFIG = {
    BIOMETRIC_LEFT_FINGERS: {"width_ratio": 0.85, "height_ratio": 0.50, "shape": "wide_rect"},
    BIOMETRIC_LEFT_THUMB: {"width_ratio": 0.55, "height_ratio": 0.50, "shape": "thumb_rect"},
    BIOMETRIC_RIGHT_FINGERS: {"width_ratio": 0.85, "height_ratio": 0.50, "shape": "wide_rect"},
    BIOMETRIC_RIGHT_THUMB: {"width_ratio": 0.55, "height_ratio": 0.50, "shape": "thumb_rect"},
}

# Standard normalized processing resolution (width, height)
# Using uniform resolution ensures consistent scale for feature extraction
ROI_WIDTH = 480
ROI_HEIGHT = 640

# DIP Quality Control Thresholds (configurable constants)
# Blur threshold based on Laplacian variance
BLUR_THRESHOLD = 80.0

# Brightness limits (average intensity [0-255])
MIN_BRIGHTNESS = 40.0
MAX_BRIGHTNESS = 225.0

# ORB Feature Extraction & Matching Configuration
ORB_N_FEATURES = 500
ORB_SCALE_FACTOR = 1.2
ORB_N_LEVELS = 8
HAMMING_GOOD_MATCH_MAX_DIST = 50.0

# Initial matching threshold - to be calibrated after real Android tests
# Score is percentage of good matches relative to total descriptors
DEFAULT_MATCH_THRESHOLD = 20.0

# Professional Academic Color Palette (RGBA for Kivy, [0.0 - 1.0])
COLOR_BG = (0.97, 0.98, 0.98, 1.0)          # Clean off-white #F8F9FA
COLOR_SURFACE = (1.0, 1.0, 1.0, 1.0)        # Pure white #FFFFFF
COLOR_PRIMARY = (0.08, 0.40, 0.75, 1.0)      # Academic Blue #1565C0
COLOR_PRIMARY_DARK = (0.05, 0.28, 0.63, 1.0) # Pressed Blue #0D47A1
COLOR_SECONDARY = (0.22, 0.28, 0.31, 1.0)   # Slate Grey #37474F
COLOR_TEXT_PRIMARY = (0.13, 0.13, 0.13, 1.0)# Almost Black #212121
COLOR_TEXT_MUTED = (0.45, 0.45, 0.45, 1.0)  # Medium Grey #757575
COLOR_BORDER = (0.85, 0.85, 0.85, 1.0)      # Light Grey border #D6D6D6
COLOR_SUCCESS = (0.18, 0.49, 0.20, 1.0)     # Green #2E7D32
COLOR_DANGER = (0.78, 0.16, 0.16, 1.0)      # Red #C62828
COLOR_OVERLAY_GUIDE = (0.08, 0.75, 0.35, 0.9)# Bright Green overlay for positioning box
