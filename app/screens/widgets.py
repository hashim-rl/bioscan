"""
Reusable UI widgets styled for BioScan.
Professional, clean Material-like design built entirely with plain Kivy.
"""

from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
from app.utils.constants import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_DARK,
    COLOR_SECONDARY,
    COLOR_SURFACE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_SUCCESS,
)


class PrimaryButton(Button):
    """Standard prominent action button."""
    def __init__(self, bg_color=COLOR_PRIMARY, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)  # Make default Kivy background transparent
        self.background_normal = ""
        self.color = (1, 1, 1, 1)
        self.font_size = "15sp"
        self.bold = True
        self.size_hint_y = None
        self.height = "48dp"
        self.normal_color = bg_color
        self.current_color = list(self.normal_color)

        with self.canvas.before:
            self.canvas_color = Color(*self.current_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])

        self.bind(pos=self._update_rect, size=self._update_rect)
        self.bind(disabled=self._disabled_style)

    def _disabled_style(self, *args):
        self.canvas_color.rgba = (0.65, 0.68, 0.72, 1) if self.disabled else self.normal_color

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_press(self):
        self.canvas_color.rgba = (
            self.normal_color[0] * 0.8,
            self.normal_color[1] * 0.8,
            self.normal_color[2] * 0.8,
            1.0,
        )

    def on_release(self):
        self.canvas_color.rgba = self.normal_color


class SecondaryButton(Button):
    """Outlined secondary button."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ""
        self.color = COLOR_PRIMARY
        self.font_size = "14sp"
        self.bold = True
        self.size_hint_y = None
        self.height = "48dp"

        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
            self.line_color = Color(*COLOR_PRIMARY)
            self.line = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 8], width=1.2)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rounded_rectangle = [self.x, self.y, self.width, self.height, 8]


class DangerButton(PrimaryButton):
    """Button for destructive actions like user deletion."""
    def __init__(self, **kwargs):
        super().__init__(bg_color=COLOR_DANGER, **kwargs)


class StyledTextInput(TextInput):
    """Clean text input with rounded border and readable font."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.size_hint_y = None
        self.height = "56dp"
        self.font_size = "15sp"
        self.padding = ["12dp", "12dp", "12dp", "12dp"]
        self.background_color = (0, 0, 0, 0)
        self.foreground_color = COLOR_TEXT_PRIMARY
        self.cursor_color = COLOR_PRIMARY
        self.hint_text_color = COLOR_TEXT_MUTED
        self.background_normal = ""
        self.background_active = ""
        self.background_color = (1, 1, 1, 1)
        # Do not append colors to canvas.before: TextInput uses its final Color
        # to render the glyphs. A border there turns active text pale grey.
        with self.canvas.after:
            self.line_color = Color(*COLOR_BORDER)
            self.line = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 6], width=1.1)

        self.bind(pos=self._update_rect, size=self._update_rect)
        self.bind(focus=self._focus_style, line_height=self._update_rect)

    def _focus_style(self, *args):
        self.line_color.rgba = COLOR_PRIMARY if self.focus else COLOR_BORDER

    def _update_rect(self, *args):
        self.line.rounded_rectangle = [self.x, self.y, self.width, self.height, 6]
        pad = max(dp(8), (self.height - self.line_height) / 2)
        self.padding = [dp(12), pad, dp(12), pad]


class CardBox(BoxLayout):
    """White card container with rounded corners."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = ["16dp", "16dp", "16dp", "16dp"]
        self.spacing = "10dp"

        with self.canvas.before:
            Color(*COLOR_SURFACE)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
            Color(*COLOR_BORDER)
            self.line = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 10], width=1.0)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rounded_rectangle = [self.x, self.y, self.width, self.height, 10]
