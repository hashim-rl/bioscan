"""
BioScan - Camera-based Biometric Image Processing Prototype
Main Application Entry Point
"""

import os
import sys
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition

# Set mobile portrait window size for desktop testing
from kivy.utils import platform
if platform != "android":
    Window.size = (390, 720)

from app.screens import (
    HomeScreen,
    RegisterScreen,
    CameraCaptureScreen,
    VerifyScreen,
    ResultScreen,
    UsersScreen,
)


class BioScanApp(App):
    title = "BioScan"

    def build(self):
        Window.softinput_mode = 'below_target'
        # Create ScreenManager with smooth cross-fade transition
        sm = ScreenManager(transition=FadeTransition(duration=0.15))

        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(RegisterScreen(name="register"))
        sm.add_widget(CameraCaptureScreen(name="camera_capture"))
        sm.add_widget(VerifyScreen(name="verify"))
        sm.add_widget(ResultScreen(name="result"))
        sm.add_widget(UsersScreen(name="users"))
        # Bind hardware back button (Android keycode 27 / Esc on desktop)
        Window.bind(on_keyboard=self._on_keyboard_handler)
        return sm

    def on_start(self):
        # Initialize SQLite database schema
        from app.services.database import init_database
        init_database()
        print("[BioScan] Local SQLite database initialized successfully.")

    def on_pause(self):
        # Native camera observes Android activity lifecycle and releases the
        # session while backgrounded. Keep the registration queue alive.
        return True

    def on_stop(self):
        if self.root:
            self.root.get_screen('camera_capture')._stop_camera()

    def _on_keyboard_handler(self, window, key, *args):
        # 27 is Android back button and Escape key on desktop
        if key == 27:
            sm = self.root
            if not sm:
                return False

            current = sm.current
            if current == "home":
                # Exit app from home screen
                return False
            elif current in ("register", "verify", "users", "result"):
                sm.current = "home"
                return True
            elif current == "camera_capture":
                cam_screen = sm.get_screen("camera_capture")
                if cam_screen.mode == "register":
                    sm.current = "register"
                else:
                    sm.current = "verify"
                return True

        return False


if __name__ == "__main__":
    BioScanApp().run()
