"""
Result Screen for BioScan.
Displays verification outcomes (REGISTERED / NOT REGISTERED)
and registration completion confirmations.
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
    COLOR_SUCCESS,
    COLOR_DANGER,
    BIOMETRIC_LABELS,
)
from app.screens.widgets import PrimaryButton, SecondaryButton, CardBox


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*COLOR_BG)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.root_layout = BoxLayout(
            orientation="vertical",
            padding=["24dp", "40dp", "24dp", "24dp"],
            spacing="16dp",
        )

        # Top spacer
        self.root_layout.add_widget(Widget(size_hint_y=0.1))

        # Outcome Header (REGISTERED / NOT REGISTERED / REGISTRATION SAVED)
        self.lbl_outcome = Label(
            text="REGISTERED",
            font_size="28sp",
            bold=True,
            color=COLOR_SUCCESS,
            size_hint_y=None,
            height="44dp",
            halign="center",
        )
        self.lbl_outcome.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        self.root_layout.add_widget(self.lbl_outcome)

        # Outcome Subtitle
        self.lbl_subtitle = Label(
            text="Biometric match verified against local registry.",
            font_size="13sp",
            color=COLOR_TEXT_MUTED,
            size_hint_y=None,
            height="24dp",
            halign="center",
        )
        self.lbl_subtitle.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        self.root_layout.add_widget(self.lbl_subtitle)

        # Details Card
        self.details_card = CardBox(size_hint_y=None)
        self.details_card.bind(minimum_height=self.details_card.setter("height"))

        self.lbl_name_row = self._create_detail_row("Name:", "Ahmed Ali")
        self.details_card.add_widget(self.lbl_name_row)

        self.lbl_id_row = self._create_detail_row("User ID:", "U-1024")
        self.details_card.add_widget(self.lbl_id_row)

        self.lbl_bio_row = self._create_detail_row("Biometric:", "Left Thumb")
        self.details_card.add_widget(self.lbl_bio_row)

        self.lbl_score_row = self._create_detail_row("Match Score:", "84.2%")
        self.details_card.add_widget(self.lbl_score_row)

        self.root_layout.add_widget(self.details_card)

        # Middle spacer
        self.root_layout.add_widget(Widget(size_hint_y=0.2))

        # Buttons Container
        self.btn_layout = BoxLayout(
            orientation="vertical",
            spacing="12dp",
            size_hint_y=None,
        )
        self.btn_layout.bind(minimum_height=self.btn_layout.setter("height"))

        self.btn_primary = PrimaryButton(text="DONE")
        self.btn_primary.bind(on_release=self._on_done)
        self.btn_layout.add_widget(self.btn_primary)

        self.btn_secondary = SecondaryButton(text="TRY AGAIN")
        self.btn_secondary.bind(on_release=self._on_try_again)
        self.btn_layout.add_widget(self.btn_secondary)

        self.root_layout.add_widget(self.btn_layout)

        # Bottom spacer
        self.root_layout.add_widget(Widget(size_hint_y=0.1))

        self.add_widget(self.root_layout)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _create_detail_row(self, title: str, value: str) -> BoxLayout:
        box = BoxLayout(orientation="horizontal", size_hint_y=None, height="26dp")
        lbl_title = Label(
            text=title,
            font_size="13sp",
            bold=True,
            color=COLOR_TEXT_MUTED,
            size_hint_x=0.4,
            halign="left",
            valign="middle",
        )
        lbl_title.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))

        lbl_val = Label(
            text=value,
            font_size="14sp",
            color=COLOR_TEXT_PRIMARY,
            size_hint_x=0.6,
            halign="left",
            valign="middle",
        )
        lbl_val.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))

        box.add_widget(lbl_title)
        box.add_widget(lbl_val)
        box.value_label = lbl_val
        return box

    def show_verification_result(self, success: bool, user_id: str = "", name: str = "", category: str = "", score: float = 0.0):
        """Configure result screen for verification."""
        if success:
            self.lbl_outcome.text = "REGISTERED"
            self.lbl_outcome.color = COLOR_SUCCESS
            self.lbl_subtitle.text = "Biometric match verified against local registry."
            self.details_card.opacity = 1
            self.details_card.disabled = False
            self.lbl_name_row.value_label.text = name
            self.lbl_id_row.value_label.text = user_id
            self.lbl_bio_row.value_label.text = BIOMETRIC_LABELS.get(category, category)
            self.lbl_score_row.value_label.text = f"{score:.1f}%"

            self.btn_primary.text = "DONE"
            self.btn_secondary.opacity = 0
            self.btn_secondary.disabled = True
        else:
            self.lbl_outcome.text = "NOT REGISTERED"
            self.lbl_outcome.color = COLOR_DANGER
            self.lbl_subtitle.text = "No matching biometric registration was found."
            self.details_card.opacity = 0
            self.details_card.disabled = True

            self.btn_primary.text = "TRY AGAIN"
            self.btn_secondary.text = "HOME"
            self.btn_secondary.opacity = 1
            self.btn_secondary.disabled = False

    def show_registration_complete(self, user_id: str, name: str, count: int):
        """Configure result screen for registration completion."""
        self.lbl_outcome.text = "REGISTRATION SAVED"
        self.lbl_outcome.color = COLOR_SUCCESS
        self.lbl_subtitle.text = "Biometric templates saved to local SQLite database."
        self.details_card.opacity = 1
        self.details_card.disabled = False
        self.lbl_name_row.value_label.text = name
        self.lbl_id_row.value_label.text = user_id
        self.lbl_bio_row.value_label.text = f"{count} biometric categories"
        self.lbl_score_row.value_label.text = "N/A (Registered)"

        self.btn_primary.text = "DONE"
        self.btn_secondary.opacity = 0
        self.btn_secondary.disabled = True

    def _on_done(self, *args):
        if self.btn_primary.text == "TRY AGAIN":
            self.manager.current = "verify"
        else:
            self.manager.current = "home"

    def _on_try_again(self, *args):
        self.manager.current = "home"
