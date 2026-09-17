# Android rescue

Baseline: 37226ec, preserved on codex/bioscan-rescue-baseline. Device: RMX3834,
ADB serial 0N14305I22104E7B. Existing failure video preserved.

Design: a Java CameraX dialog owns native PreviewView, guide, focus and JPEG
capture. Kivy owns the existing workflow and review. Camera4Kivy was considered
but is archived; a direct bridge avoids its old provider and preview texture path.
CameraX Preview + ImageCapture share a FILL_CENTER ViewPort. Saved JPEGs have
the viewport crop applied; Pillow applies EXIF before the guide is mapped.
Only still images enter Python/OpenCV. No Android simulated fallback.

1. Add failing geometry tests for aspect fill, rotation, mirroring and viewport
   JPEG mapping. Implement app/services/camera_geometry.py.
2. Add native/org/bioscan/camera/ScanCamera.java and Python lifecycle wrapper.
   Pin CameraX 1.3.4 (API 34 compatible), enable AndroidX in Buildozer.
3. Integrate asynchronous still processing and single-image review toggle.
4. Fix TextInput canvas color leakage, focus styling, selectable rows and scrolling.
5. Regression tests, branch build through existing GitHub Actions, ADB install.
6. Device screenshots/logs, camera/lifecycle/registration/persistence checks.
   Human-held focused fingers and genuine/impostor trials require user participation.

Keep SQLite, categories, descriptors and Base64 interfaces. Keep current thresholds
provisional and configurable; do not claim calibration without actual samples.
