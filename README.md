# BioScan — Camera-Based Biometric Image Processing Prototype

**BioScan** is an academic, university-grade biometric image processing and verification prototype application for Android, written primarily in **Python** using **Kivy**, **OpenCV**, **NumPy**, and **SQLite**.

> **Important Academic Disclaimer**:  
> This project is a camera-based biometric image processing prototype designed for academic demonstrations and image processing experiments. Normal smartphone cameras do not possess optical prism or capacitive fingerprint hardware and are **NOT** certified for banking-grade, cryptographic, or high-security biometric authentication.

---

## 1. Application Overview & Features

- **100% Local & Offline**: Completely self-contained. No Firebase, no cloud APIs, no external web servers.
- **Biometric Categories (1 to 4)**:
  1. *Left Hand — 4 Fingers* (`LEFT_FINGERS`)
  2. *Left Thumb* (`LEFT_THUMB`)
  3. *Right Hand — 4 Fingers* (`RIGHT_FINGERS`)
  4. *Right Thumb* (`RIGHT_THUMB`)
- **Category-Specific Positioning Guides**: Dynamic on-screen overlays (wide rectangle for 4 fingers, centered box for thumb) ensure consistent capture alignment across registration and verification.
- **Digital Image Processing (DIP) Pipeline**: Real-time cropping, grayscale conversion, illumination and blur quality checks, CLAHE contrast enhancement, edge-preserving bilateral filtering, and unsharp masking.
- **Side-by-Side Review**: Immediate visual inspection of Original ROI vs. Enhanced image prior to accepting scan.
- **Base64 Image Encoding**: Reversible encoding of enhanced image bytes for standardized SQLite storage and display interchange (never used for comparison).
- **ORB Feature Extraction & Matching**: Binary descriptor extraction (500 features, 32-byte descriptors), serialized to SQLite BLOB, compared using OpenCV BFMatcher with Hamming distance.
- **Category-Isolated Verification**: Matching is restricted strictly to the identical biometric category (e.g. Left Thumb is never compared against Right Fingers).
- **User Management**: Demonstration user list with identity details and cascaded deletion (`PRAGMA foreign_keys = ON;`).

---

## 2. Technology Stack

- **Application Language**: Python 3.10+ / 3.13
- **User Interface**: Plain Kivy 2.3+ (custom Material-styled components, avoiding KivyMD dependency churn)
- **Computer Vision & DIP**: OpenCV (`opencv-python` / OpenCV 5.0)
- **Matrix Operations**: NumPy
- **Database**: Local SQLite3 with foreign key cascade support
- **Packaging & Build System**: Buildozer / python-for-android (targeting Android API 34, min API 24)

---

## 3. Project Architecture

```
bioscan/
├── main.py                     # Application entry point, ScreenManager & Android lifecycle
├── buildozer.spec              # Android APK build specification
├── requirements.txt            # Python development requirements
├── .github/
│   └── workflows/
│       └── build-apk.yml       # Cloud automated APK builder (GitHub Actions)
├── app/
│   ├── screens/
│   │   ├── home.py             # Home screen (Register, Verify, Manage Users)
│   │   ├── register.py         # Registration form (Name, User ID, 4 Category checkboxes)
│   │   ├── camera_capture.py   # Camera preview, positioning guides, snapshot review, accept/retake
│   │   ├── verify.py           # Category selection for verification
│   │   ├── result.py           # Verification outcome (REGISTERED / NOT REGISTERED)
│   │   ├── users.py            # Simple user management & demo deletion
│   │   └── widgets.py          # Custom Material-styled Kivy widgets
│   ├── services/
│   │   ├── database.py         # SQLite schema, CRUD operations, PRAGMA foreign_keys=ON
│   │   ├── image_processor.py  # DIP enhancement pipeline, quality checks, Base64 conversion
│   │   └── recognition.py      # ORB feature detector, descriptor serialization, BFMatcher
│   └── utils/
│       ├── constants.py        # Categories, thresholds, UI dimensions, colors
│       └── helpers.py          # Android runtime permissions & camera orientation helper
└── tests/
    ├── test_screens.py         # Milestone 1: Screen instantiation & navigation
    ├── test_database.py        # Milestone 2: SQLite CRUD, foreign keys & cascade
    ├── test_image_processor.py # Milestone 4 & 5: DIP pipeline, quality checks & Base64
    ├── test_recognition.py     # Milestone 7: ORB extraction, serialization & matcher
    └── test_integration.py     # Milestone 8: Full 10 test case end-to-end integration
```

---

## 4. Digital Image Processing (DIP) Pipeline

The enhancement pipeline in `app/services/image_processor.py` prepares camera captures for feature matching:

1. **Acquisition & Orientation**: Raw camera frame captured as BGR matrix. Isolated camera orientation correction applied.
2. **Normalized ROI Cropping**: Frame cropped using relative bounding box ratios defined in `GUIDE_CONFIG` (matching the green on-screen positioning box exactly).
3. **Resizing**: Standardized to `480 x 640` resolution using area interpolation (`cv2.INTER_AREA`).
4. **Grayscale Conversion**: Intensity reduction from BGR to 8-bit single channel.
5. **Quality Assessment**:
   - *Illumination*: Evaluates mean intensity. Rejects underexposed (\(< 40\)) or overexposed (\(> 225\)) frames.
   - *Blur Detection*: Computes Laplacian variance \(\sigma^2\). Rejects motion-blurred captures (\(\sigma^2 < 80.0\)).
6. **CLAHE Enhancement**: Contrast-Limited Adaptive Histogram Equalization (`clipLimit=2.5`, `tileGridSize=(8, 8)`) amplifies ridge and crease gradients locally without noise saturation.
7. **Bilateral Filtering**: Edge-preserving denoising (`d=5`, `sigmaColor=50`, `sigmaSpace=50`) smooths fine skin pores while retaining sharp ridge contours.
8. **Unsharp Masking**: High-pass boost (\(1.5 \times \text{denoised} - 0.5 \times \text{gaussian\_blurred}\)) sharpens ridge contours.
9. **Intensity Normalization**: Scaled to full 0–255 dynamic range.

---

## 5. Base64 Encoding vs. Feature Matching

| Concept | Implementation | Purpose |
| :--- | :--- | :--- |
| **Base64 String** | `cv2.imencode('.png')` \(\rightarrow\) `base64.b64encode` | **Storage & Serialization Only**: Encodes enhanced images as text strings in the SQLite `image_base64` column for safe offline persistence and UI inspection. Base64 strings are **never** compared for recognition. |
| **ORB Descriptors** | `cv2.ORB_create()` \(\rightarrow\) `(N, 32)` uint8 | **Biometric Matching**: Extracts scale- and rotation-invariant keypoint descriptors. Descriptors are serialized into binary BLOBs and matched via Hamming distance. |

---

## 6. SQLite Database Design

Database file: `bioscan.db` stored in app-private storage (`user_data_dir`).

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
```

### Key Integrity Rules:
- `PRAGMA foreign_keys = ON;` is executed on every connection.
- `ON DELETE CASCADE` automatically and atomically removes all biometric templates when a user is deleted from the `users` table.
- `UNIQUE(user_id, biometric_type)` prevents the same user from registering duplicate records for the same category.

---

## 7. Biometric Feature Extraction & Matching

1. **Feature Detection**: OpenCV ORB extracts up to 500 keypoints and binary 32-byte descriptors.
2. **Serialization**: Validated uint8 contiguous array serialized to bytes with length checked against multiples of 32.
3. **Descriptor Matching**: `cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)` finds mutual nearest neighbors.
4. **Good Match Filtering**: Matches with Hamming distance \(\le 50.0\) are retained as good matches.
5. **Score Formula**:
   $$\text{Score} = \min\left(100.0, \frac{\text{Good Matches}}{\min(\text{len}(desc_{\text{query}}), \text{len}(desc_{\text{template}}))} \times 100.0\right)$$
6. **Threshold**: Compared against `DEFAULT_MATCH_THRESHOLD = 20.0%`. If \(\ge \text{threshold}\), result is **REGISTERED**; otherwise **NOT REGISTERED**.

---

## 8. Installation & Desktop Testing

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13
- pip

### Install Dependencies
```bash
cd bioscan
pip install kivy[base] opencv-python numpy pillow
```

### Run Application
```bash
python main.py
```
*Note: On desktop environments without a physical webcam, BioScan automatically engages its simulated pattern feed so that UI, capture review, DIP enhancement, registration, and verification can be tested immediately.*

### Run Automated Tests
```bash
# Test 1: Screen Instantiation and Transitions
python tests/test_screens.py

# Test 2: SQLite Database & Foreign Key Cascade
python tests/test_database.py

# Test 3: DIP Pipeline, Quality Checks & Base64
python tests/test_image_processor.py

# Test 4: ORB Feature Extraction & Matching
python tests/test_recognition.py

# Test 5: All 10 Integration Workflow Test Cases
python tests/test_integration.py
```

---

## 9. Building the Android APK

### Option A: Cloud Automated Build (GitHub Actions — Recommended)
1. Push this repository to GitHub.
2. Navigate to **Actions** \(\rightarrow\) **Build BioScan Android APK** \(\rightarrow\) **Run workflow**.
3. Download the generated `BioScan-debug-apk` artifact containing the installable `.apk`.

### Option B: Local Build via WSL / Ubuntu Linux
Buildozer requires a POSIX environment with Linux cross-compilers:
```bash
# 1. Install system prerequisites (Ubuntu / WSL)
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# 2. Install Buildozer
pip install --upgrade buildozer cython virtualenv

# 3. Build APK
buildozer android debug
```
The resulting APK will be generated in `bin/bioscan-1.0.0-arm64-v8a_armeabi-v7a-debug.apk`.

---

## 10. Known Academic Limitations

1. **Camera Sensor vs. Dedicated Sensor**: Mobile camera sensors capture reflected light from the surface of fingers. Factors like illumination, distance, and finger placement angle introduce variability compared to dedicated optical FTIR or capacitive fingerprint scanners.
2. **Skin Elasticity**: Pressing fingers against glass creates distinct deformation patterns; free-air camera captures require steady alignment within the on-screen guide overlay.
3. **Threshold Calibration**: The default threshold (`MATCH_THRESHOLD = 20.0`) is configured for prototype demonstration and can be fine-tuned in `app/utils/constants.py` after testing on specific hardware.
