"""
Camera Capture Screen for BioScan.
Handles real-time camera preview, category-specific positioning overlays,
snapshot capture, and post-capture Original vs Enhanced inspection.
"""

import io
import cv2
import numpy as np
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line
from kivy.core.image import Image as CoreImage

from app.utils.constants import (
    COLOR_BG,
    COLOR_PRIMARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_OVERLAY_GUIDE,
    COLOR_DANGER,
    COLOR_SUCCESS,
    BIOMETRIC_LEFT_FINGERS,
    BIOMETRIC_LEFT_THUMB,
    BIOMETRIC_RIGHT_FINGERS,
    BIOMETRIC_RIGHT_THUMB,
    BIOMETRIC_LABELS,
    BIOMETRIC_INSTRUCTIONS,
    GUIDE_CONFIG,
    ROI_WIDTH,
    ROI_HEIGHT,
)
from app.screens.widgets import PrimaryButton, SecondaryButton
from app.utils.helpers import is_android, request_android_camera_permission, adjust_camera_orientation


class PositioningOverlayWidget(Widget):
    """
    Renders a dynamic guide box on top of the camera preview.
    Draws a wide rectangular box for 4 fingers, or a compact centered box for thumb.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.category = BIOMETRIC_LEFT_FINGERS
        self.guide_rect = (0, 0, 100, 100)
        self.bind(pos=self._redraw, size=self._redraw)

    def set_category(self, category: str):
        self.category = category
        self._redraw()

    def _redraw(self, *args):
        self.canvas.clear()
        if not self.width or not self.height:
            return

        cfg = GUIDE_CONFIG.get(self.category, GUIDE_CONFIG[BIOMETRIC_LEFT_FINGERS])
        w_ratio = cfg["width_ratio"]
        h_ratio = cfg["height_ratio"]

        box_w = self.width * w_ratio
        box_h = self.height * h_ratio
        box_x = self.x + (self.width - box_w) / 2.0
        box_y = self.y + (self.height - box_h) / 2.0

        self.guide_rect = (box_x, box_y, box_w, box_h)

        with self.canvas:
            # Semi-transparent dimmed surrounding mask
            Color(0, 0, 0, 0.45)
            # Top mask
            Rectangle(pos=(self.x, box_y + box_h), size=(self.width, max(0, self.y + self.height - (box_y + box_h))))
            # Bottom mask
            Rectangle(pos=(self.x, self.y), size=(self.width, max(0, box_y - self.y)))
            # Left mask
            Rectangle(pos=(self.x, box_y), size=(max(0, box_x - self.x), box_h))
            # Right mask
            Rectangle(pos=(box_x + box_w, box_y), size=(max(0, self.x + self.width - (box_x + box_w)), box_h))

            # Bright guide border
            Color(*COLOR_OVERLAY_GUIDE)
            Line(rounded_rectangle=[box_x, box_y, box_w, box_h, 12], width=2.5)

            # Corner target ticks for alignment precision
            tick_len = 24
            # Bottom-left
            Line(points=[box_x, box_y + tick_len, box_x, box_y, box_x + tick_len, box_y], width=3.5)
            # Top-left
            Line(points=[box_x, box_y + box_h - tick_len, box_x, box_y + box_h, box_x + tick_len, box_y + box_h], width=3.5)
            # Bottom-right
            Line(points=[box_x + box_w - tick_len, box_y, box_x + box_w, box_y, box_x + box_w, box_y + tick_len], width=3.5)
            # Top-right
            Line(points=[box_x + box_w - tick_len, box_y + box_h, box_x + box_w, box_y + box_h, box_x + box_w, box_y + box_h - tick_len], width=3.5)


class CameraCaptureScreen(Screen):
    """
    Handles camera capture for both Registration and Verification workflows.
    Includes simulated fallback feed for reliable desktop debugging without webcams.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.mode = "register"  # "register" or "verify"
        self.user_id = ""
        self.user_name = ""
        self.category_queue = []
        self.current_category_idx = 0
        self.captured_records = []

        # Current captured frame and enhanced frame (numpy arrays)
        self.captured_raw_frame = None
        self.enhanced_frame = None

        # Camera variables
        self.kivy_camera = None
        self.camera_active = False
        self.simulated_cam_event = None

        self._build_ui()

    def _build_ui(self):
        with self.canvas.before:
            Color(*COLOR_BG)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        main_layout = BoxLayout(
            orientation="vertical",
            padding=["16dp", "16dp", "16dp", "16dp"],
            spacing="10dp",
        )

        # Header Area
        self.lbl_title = Label(
            text="Biometric Capture",
            font_size="18sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height="28dp",
            halign="center",
        )
        self.lbl_title.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        main_layout.add_widget(self.lbl_title)

        self.lbl_instructions = Label(
            text="Position fingers inside the guide box.",
            font_size="13sp",
            color=COLOR_TEXT_PRIMARY,
            size_hint_y=None,
            height="26dp",
            halign="center",
        )
        self.lbl_instructions.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        main_layout.add_widget(self.lbl_instructions)

        # Camera / Preview Viewport (FloatLayout holds camera + guide overlay)
        self.viewport = FloatLayout(size_hint=(1, 1))

        # Camera widget placeholder
        self.cam_container = BoxLayout(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.viewport.add_widget(self.cam_container)

        # Post-capture preview display (Original & Enhanced side by side or single)
        self.preview_image = Image(
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            allow_stretch=True,
            keep_ratio=True,
        )
        self.preview_image.opacity = 0
        self.viewport.add_widget(self.preview_image)

        # Guide overlay widget
        self.overlay_widget = PositioningOverlayWidget(
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.viewport.add_widget(self.overlay_widget)

        main_layout.add_widget(self.viewport)

        # Quality warning / Status message
        self.lbl_status = Label(
            text="",
            font_size="13sp",
            color=COLOR_DANGER,
            size_hint_y=None,
            height="24dp",
            halign="center",
        )
        self.lbl_status.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        main_layout.add_widget(self.lbl_status)

        # Bottom Controls: State 1 (Live Preview: Capture & Cancel)
        self.live_controls = BoxLayout(
            orientation="horizontal",
            spacing="12dp",
            size_hint_y=None,
            height="50dp",
        )
        self.btn_cancel = SecondaryButton(text="Cancel")
        self.btn_cancel.bind(on_release=self._on_cancel)
        self.live_controls.add_widget(self.btn_cancel)

        self.btn_capture = PrimaryButton(text="CAPTURE IMAGE")
        self.btn_capture.bind(on_release=self._on_capture)
        self.live_controls.add_widget(self.btn_capture)

        main_layout.add_widget(self.live_controls)

        # Bottom Controls: State 2 (Inspection: Retake & Accept)
        self.review_controls = BoxLayout(
            orientation="horizontal",
            spacing="12dp",
            size_hint_y=None,
            height="50dp",
        )
        self.btn_retake = SecondaryButton(text="RETAKE")
        self.btn_retake.bind(on_release=self._on_retake)
        self.review_controls.add_widget(self.btn_retake)

        self.btn_accept = PrimaryButton(text="ACCEPT SCAN", bg_color=COLOR_SUCCESS)
        self.btn_accept.bind(on_release=self._on_accept)
        self.review_controls.add_widget(self.btn_accept)

        # Initially hide review controls
        self.review_controls.opacity = 0
        self.review_controls.disabled = True
        main_layout.add_widget(self.review_controls)

        self.add_widget(main_layout)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def setup_registration_flow(self, user_id: str, name: str, categories_to_capture: list):
        """Prepares sequential capture for user registration."""
        self.mode = "register"
        self.user_id = user_id
        self.user_name = name
        self.category_queue = list(categories_to_capture)
        self.current_category_idx = 0
        self.captured_records = []

    def setup_verification_flow(self, category_to_verify: str):
        """Prepares single capture for verification."""
        self.mode = "verify"
        self.user_id = ""
        self.user_name = ""
        self.category_queue = [category_to_verify]
        self.current_category_idx = 0
        self.captured_records = []

    def on_pre_enter(self):
        """Called before screen is shown; initialize camera and UI."""
        self._show_live_state()
        self._update_step_labels()
        self._start_camera()

    def on_leave(self):
        """Clean up and release camera when leaving screen."""
        self._stop_camera()

    def _update_step_labels(self):
        if not self.category_queue:
            return

        cat = self.category_queue[self.current_category_idx]
        cat_name = BIOMETRIC_LABELS.get(cat, cat)
        total = len(self.category_queue)
        curr = self.current_category_idx + 1

        if self.mode == "register":
            self.lbl_title.text = f"Step {curr}/{total}: {cat_name}"
        else:
            self.lbl_title.text = f"Verify: {cat_name}"

        self.lbl_instructions.text = BIOMETRIC_INSTRUCTIONS.get(cat, "Place hand within guide.")
        self.overlay_widget.set_category(cat)

    def _start_camera(self):
        """Initialize camera widget or fallback."""
        self._stop_camera()

        def on_permission_granted(granted):
            if not granted:
                self.lbl_status.text = "Camera permission denied."
                self._start_simulated_feed()
                return

            try:
                from kivy.uix.camera import Camera
                self.kivy_camera = Camera(play=True, resolution=(640, 480))
                self.cam_container.clear_widgets()
                self.cam_container.add_widget(self.kivy_camera)
                self.camera_active = True
                self.lbl_status.text = ""
            except Exception as e:
                print(f"[BioScan Camera] Hardware camera init failed: {e}")
                self._start_simulated_feed()

        request_android_camera_permission(on_permission_granted)

    def _start_simulated_feed(self):
        """Fallback simulated feed for desktop testing when camera is absent."""
        self.cam_container.clear_widgets()
        simulated_img = Image(size_hint=(1, 1), allow_stretch=True, keep_ratio=True)
        self.cam_container.add_widget(simulated_img)

        def update_simulated(dt):
            # Generate a synthetic patterned hand/fingerprint matrix
            h, w = 480, 640
            frame = np.full((h, w, 3), 235, dtype=np.uint8)

            # Draw simulated finger ridge patterns
            center_x, center_y = w // 2, h // 2
            for r in range(20, 180, 8):
                cv2.ellipse(frame, (center_x, center_y), (r, int(r * 1.4)), 0, 0, 360, (50, 50, 50), 2)

            buf = cv2.flip(frame, 0).tobytes()
            core_img = CoreImage(io.BytesIO(cv2.imencode('.png', cv2.flip(frame, 0))[1]), ext='png')
            simulated_img.texture = core_img.texture
            self.captured_raw_frame = frame

        self.simulated_cam_event = Clock.schedule_interval(update_simulated, 1.0 / 15.0)
        self.camera_active = True
        self.lbl_status.text = "Simulated feed active (desktop dev mode)"

    def _stop_camera(self):
        if self.simulated_cam_event:
            self.simulated_cam_event.cancel()
            self.simulated_cam_event = None

        if self.kivy_camera:
            try:
                self.kivy_camera.play = False
            except Exception:
                pass
            self.cam_container.clear_widgets()
            self.kivy_camera = None

        self.camera_active = False

    def _get_current_frame(self) -> np.ndarray:
        """Extracts current frame from active camera as BGR numpy array."""
        if self.kivy_camera and self.kivy_camera.texture:
            tex = self.kivy_camera.texture
            size = tex.size
            pixels = tex.pixels
            # Kivy camera texture is RGBA
            img_rgba = np.frombuffer(pixels, dtype=np.uint8).reshape((size[1], size[0], 4))
            img_bgr = cv2.cvtColor(img_rgba, cv2.COLOR_RGBA2BGR)
            # Adjust isolated orientation for camera
            return adjust_camera_orientation(img_bgr)

        if self.captured_raw_frame is not None:
            return self.captured_raw_frame.copy()

        # Fallback empty frame
        return np.full((480, 640, 3), 180, dtype=np.uint8)

    def _show_live_state(self):
        """Switches controls and visibility to live preview state."""
        self.cam_container.opacity = 1
        self.overlay_widget.opacity = 1
        self.preview_image.opacity = 0
        self.live_controls.opacity = 1
        self.live_controls.disabled = False
        self.review_controls.opacity = 0
        self.review_controls.disabled = True
        self.lbl_status.text = ""

    def _show_review_state(self, preview_texture):
        """Switches controls and visibility to captured review state."""
        self.preview_image.texture = preview_texture
        self.preview_image.opacity = 1
        self.overlay_widget.opacity = 0
        self.live_controls.opacity = 0
        self.live_controls.disabled = True
        self.review_controls.opacity = 1
        self.review_controls.disabled = False

    def _create_side_by_side_preview(self, orig_roi: np.ndarray, enhanced: np.ndarray) -> np.ndarray:
        """Creates a side-by-side comparison image of Original vs Enhanced for review."""
        disp_w, disp_h = 240, 320
        orig_resized = cv2.resize(orig_roi, (disp_w, disp_h))
        enh_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        enh_resized = cv2.resize(enh_bgr, (disp_w, disp_h))

        # Annotate labels for academic demonstration
        cv2.putText(orig_resized, "ORIGINAL", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 0), 2)
        cv2.putText(enh_resized, "ENHANCED", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 0), 2)

        # Thin visual divider
        divider = np.full((disp_h, 3, 3), 200, dtype=np.uint8)
        return np.hstack((orig_resized, divider, enh_resized))

    def _on_capture(self, *args):
        frame = self._get_current_frame()
        self.captured_raw_frame = frame
        current_cat = self.category_queue[self.current_category_idx]

        try:
            from app.services.image_processor import preprocess_image
            orig_roi, enhanced, quality = preprocess_image(frame, current_cat)
            self.current_roi = orig_roi
            self.current_enhanced = enhanced
            self.current_quality = quality

            comparison = self._create_side_by_side_preview(orig_roi, enhanced)
            buf = cv2.imencode('.png', comparison)[1].tobytes()
            core_img = CoreImage(io.BytesIO(buf), ext='png')
            self._show_review_state(core_img.texture)

            if not quality["passed"]:
                self.lbl_status.text = f"Quality Warning: {quality['reason']}"
                self.btn_accept.disabled = True
            else:
                self.lbl_status.text = (
                    f"DIP Enhanced. Sharpness: {quality['blur_score']:.0f} | Brightness: {quality['mean_brightness']:.0f}"
                )
                self.btn_accept.disabled = False
        except Exception as e:
            print(f"[BioScan Capture Error] {e}")
            self.lbl_status.text = f"Processing error: {e}"
            self._show_live_state()

    def _on_retake(self, *args):
        self._show_live_state()

    def _on_accept(self, *args):
        if not hasattr(self, "current_enhanced") or self.current_enhanced is None:
            self._show_live_state()
            return

        current_cat = self.category_queue[self.current_category_idx]

        try:
            from app.services.image_processor import image_to_base64
            from app.services.recognition import extract_features, serialize_descriptors

            b64_str = image_to_base64(self.current_enhanced)
            _, desc = extract_features(self.current_enhanced)
            feat_bytes = serialize_descriptors(desc)

            self.captured_records.append({
                "category": current_cat,
                "image_base64": b64_str,
                "feature_data": feat_bytes,
                "descriptors": desc,
            })
        except Exception as e:
            print(f"[BioScan Accept Error] {e}")
            self.lbl_status.text = f"Feature extraction error: {e}"
            return

        self.current_category_idx += 1
        if self.current_category_idx < len(self.category_queue):
            # Advance to next category in registration queue
            self._show_live_state()
            self._update_step_labels()
        else:
            # All captures completed
            self._finish_flow()

    def _finish_flow(self):
        if self.mode == "register":
            from app.services.database import get_user, create_user, save_biometric

            # Create user if new
            if not get_user(self.user_id):
                create_user(self.user_id, self.user_name)

            # Persist biometrics
            saved_count = 0
            for rec in self.captured_records:
                ok = save_biometric(
                    user_id=self.user_id,
                    biometric_type=rec["category"],
                    image_base64=rec["image_base64"],
                    feature_data=rec["feature_data"],
                )
                if ok:
                    saved_count += 1

            res_screen = self.manager.get_screen("result")
            res_screen.show_registration_complete(
                user_id=self.user_id,
                name=self.user_name,
                count=saved_count,
            )
            self.manager.current = "result"
        else:
            # Verification flow
            from app.services.recognition import verify_against_templates
            from app.utils.constants import DEFAULT_MATCH_THRESHOLD

            if not self.captured_records:
                return

            rec = self.captured_records[0]
            category = rec["category"]
            res = verify_against_templates(
                query_descriptors=rec["descriptors"],
                category=category,
                threshold=DEFAULT_MATCH_THRESHOLD,
            )

            res_screen = self.manager.get_screen("result")
            if res["matched"]:
                res_screen.show_verification_result(
                    success=True,
                    user_id=res["user_id"],
                    name=res["name"],
                    category=category,
                    score=res["best_score"],
                )
            else:
                res_screen.show_verification_result(
                    success=False,
                    user_id="",
                    name="",
                    category=category,
                    score=res["best_score"],
                )
            self.manager.current = "result"

    def _on_cancel(self, *args):
        if self.mode == "register":
            self.manager.current = "register"
        else:
            self.manager.current = "verify"
