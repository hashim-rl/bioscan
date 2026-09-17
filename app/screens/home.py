"""
Home Screen for BioScan.
Professional academic biometric verification prototype start screen.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

from app.utils.constants import (
    COLOR_BG,
    COLOR_PRIMARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
)
from app.screens.widgets import PrimaryButton, SecondaryButton


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Set screen background color
        with self.canvas.before:
            Color(*COLOR_BG)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Main vertical container
        root_layout = BoxLayout(
            orientation="vertical",
            padding=["24dp", "40dp", "24dp", "24dp"],
            spacing="16dp",
        )

        # Top spacer
        root_layout.add_widget(Widget(size_hint_y=0.15))

        # App Title
        title_label = Label(
            text="BioScan",
            font_size="34sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height="48dp",
        )
        root_layout.add_widget(title_label)

        # App Subtitle
        subtitle_label = Label(
            text="Biometric Verification Prototype",
            font_size="16sp",
            color=COLOR_TEXT_MUTED,
            size_hint_y=None,
            height="28dp",
        )
        root_layout.add_widget(subtitle_label)

        # Middle spacer
        root_layout.add_widget(Widget(size_hint_y=0.25))

        # Action Buttons Layout
        btn_layout = BoxLayout(
            orientation="vertical",
            spacing="14dp",
            size_hint_y=None,
        )
        btn_layout.bind(minimum_height=btn_layout.setter("height"))

        btn_register = PrimaryButton(text="REGISTER NEW USER")
        btn_register.bind(on_release=self._go_register)
        btn_layout.add_widget(btn_register)

        btn_verify = PrimaryButton(text="VERIFY USER")
        btn_verify.bind(on_release=self._go_verify)
        btn_layout.add_widget(btn_verify)

        btn_manage = SecondaryButton(text="Manage Registered Users")
        btn_manage.bind(on_release=self._go_manage)
        btn_layout.add_widget(btn_manage)

        root_layout.add_widget(btn_layout)

        # Bottom spacer
        root_layout.add_widget(Widget(size_hint_y=0.4))

        # Bottom academic footer disclaimer
        footer_label = Label(
            text="Camera-based biometric image processing prototype\nUniversity Demonstration",
            font_size="11sp",
            color=COLOR_TEXT_MUTED,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height="40dp",
        )
        footer_label.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        root_layout.add_widget(footer_label)

        self.add_widget(root_layout)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _go_register(self, *args):
        self.manager.current = "register"

    def _go_verify(self, *args):
        self.manager.current = "verify"

    def _go_manage(self, *args):
        self.manager.current = "users"
