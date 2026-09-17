"""
Verify Screen for BioScan.
Allows selecting which biometric category is being scanned for verification.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line

from app.utils.constants import (
    COLOR_BG,
    COLOR_SURFACE,
    COLOR_PRIMARY,
    COLOR_PRIMARY_DARK,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_BORDER,
    COLOR_DANGER,
    BIOMETRIC_CATEGORIES,
    BIOMETRIC_LABELS,
)
from app.screens.widgets import PrimaryButton, SecondaryButton, CardBox


class CategorySelectButton(Button):
    """Selectable card button for biometric category."""
    def __init__(self, cat_id: str, label_text: str, is_selected: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.cat_id = cat_id
        self.label_text = label_text
        self.is_selected = is_selected

        self.background_color = (0, 0, 0, 0)
        self.background_normal = ""
        self.size_hint_y = None
        self.height = "52dp"
        self.text = label_text
        self.font_size = "14sp"
        self.bold = True

        with self.canvas.before:
            self.bg_color = Color(*COLOR_SURFACE)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
            self.border_color = Color(*COLOR_BORDER)
            self.line = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 8], width=1.2)

        self.bind(pos=self._update_rect, size=self._update_rect)
        self.update_selection_style()

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rounded_rectangle = [self.x, self.y, self.width, self.height, 8]

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_selection_style()

    def update_selection_style(self):
        if self.is_selected:
            self.bg_color.rgba = (0.90, 0.94, 0.98, 1.0)
            self.border_color.rgba = COLOR_PRIMARY
            self.line.width = 2.0
            self.color = COLOR_PRIMARY
        else:
            self.bg_color.rgba = COLOR_SURFACE
            self.border_color.rgba = COLOR_BORDER
            self.line.width = 1.2
            self.color = COLOR_TEXT_PRIMARY


class VerifyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.selected_category = BIOMETRIC_CATEGORIES[0]
        self.cat_buttons = {}

        with self.canvas.before:
            Color(*COLOR_BG)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content_box = BoxLayout(
            orientation="vertical",
            padding=["20dp", "30dp", "20dp", "24dp"],
            spacing="16dp",
            size_hint_y=None,
        )
        content_box.bind(minimum_height=content_box.setter("height"))

        # Header
        header = Label(
            text="Verify Identity",
            font_size="24sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height="36dp",
            halign="left",
        )
        header.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        content_box.add_widget(header)

        sub_header = Label(
            text="Select which biometric category you are scanning:",
            font_size="13sp",
            color=COLOR_TEXT_MUTED,
            size_hint_y=None,
            height="24dp",
            halign="left",
        )
        sub_header.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        content_box.add_widget(sub_header)

        # Category selection container
        cat_box = CardBox(size_hint_y=None)
        cat_box.bind(minimum_height=cat_box.setter("height"))

        for cat in BIOMETRIC_CATEGORIES:
            btn = CategorySelectButton(
                cat_id=cat,
                label_text=BIOMETRIC_LABELS[cat],
                is_selected=(cat == self.selected_category),
            )
            btn.bind(on_release=self._on_category_select)
            self.cat_buttons[cat] = btn
            cat_box.add_widget(btn)

        content_box.add_widget(cat_box)

        # Status warning
        self.lbl_warning = Label(
            text="",
            font_size="13sp",
            color=COLOR_DANGER,
            size_hint_y=None,
            height="24dp",
            halign="center",
        )
        self.lbl_warning.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        content_box.add_widget(self.lbl_warning)

        # Action Buttons
        btn_open_cam = PrimaryButton(text="OPEN CAMERA")
        btn_open_cam.bind(on_release=self._open_camera)
        content_box.add_widget(btn_open_cam)

        btn_back = SecondaryButton(text="Back to Home")
        btn_back.bind(on_release=self._go_home)
        content_box.add_widget(btn_back)

        scroll.add_widget(content_box)
        self.add_widget(scroll)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _on_category_select(self, instance):
        self.selected_category = instance.cat_id
        for cat, btn in self.cat_buttons.items():
            btn.set_selected(cat == self.selected_category)

    def _open_camera(self, *args):
        cam_screen = self.manager.get_screen("camera_capture")
        cam_screen.setup_verification_flow(self.selected_category)
        self.manager.current = "camera_capture"

    def _go_home(self, *args):
        self.manager.current = "home"
