[app]

# (str) Title of your application
title = BioScan

# (str) Package name
package.name = bioscan

# (str) Package domain (needed for android/ios packaging)
package.domain = org.bioscan.prototype

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,spec

# (list) List of directory to exclude
source.exclude_dirs = tests, bin, .git, .github, .gemini, p4a-recipes, docs, native
source.exclude_patterns = bioscan_*.png,failure-frame.jpg,real_device_failure.mp4

# (str) Application versioning
version = 1.1.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,opencv,numpy,pillow

android.enable_androidx = True
android.add_src = native
android.gradle_dependencies = androidx.camera:camera-core:1.3.4,androidx.camera:camera-camera2:1.3.4,androidx.camera:camera-lifecycle:1.3.4,androidx.camera:camera-view:1.3.4

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = CAMERA

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 24

# (int) Android NDK API to use.
android.ndk_api = 24

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (list) The Android architectures to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (str) The format used to package the app for release mode (aab or apk)
android.release_artifact = apk

# (bool) If True, then the app will be built as an Android App Bundle
android.aab = False

# (bool) If True, skip attempting to build with pre-installed recipes
p4a.branch = master

# (str) The directory in which python-for-android should look for your own recipes
p4a.local_recipes = ./p4a-recipes

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
