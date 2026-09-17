"""
Register Screen for BioScan.
User identity input (Name, User ID) and biometric category selector.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

from app.utils.constants import (
    COLOR_BG,
    COLOR_PRIMARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_DANGER,
    BIOMETRIC_CATEGORIES,
    BIOMETRIC_LABELS,
)
from app.screens.widgets import (
    PrimaryButton,
    SecondaryButton,
    StyledTextInput,
    CardBox,
)


class BiometricCheckItem(BoxLayout):
    """Row displaying a checkbox and the biometric category label."""
    def __init__(self, cat_id: str, label_text: str, **kwargs):
        super().__init__(**kwargs)
        self.cat_id = cat_id
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = "40dp"
        self.spacing = "10dp"

        self.checkbox = CheckBox(
            size_hint=(None, None),
            size=("30dp", "30dp"),
            color=(0.08, 0.40, 0.75, 1.0),
        )
        self.add_widget(self.checkbox)

        self.label = Label(
            text=label_text,
            font_size="14sp",
            color=COLOR_TEXT_PRIMARY,
            halign="left",
            valign="middle",
        )
        self.label.bind(size=lambda lbl, sz: setattr(lbl, "text_size", (sz[0], None)))
        self.add_widget(self.label)

    @property
    def is_checked(self) -> bool:
        return self.checkbox.active

    @is_checked.setter
    def is_checked(self, val: bool):
        self.checkbox.active = val


class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*COLOR_BG)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Main layout wrapped in ScrollView for small phone displays
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content_box = BoxLayout(
            orientation="vertical",
            padding=["20dp", "24dp", "20dp", "24dp"],
            spacing="14dp",
            size_hint_y=None,
        )
        content_box.bind(minimum_height=content_box.setter("height"))

        # Screen Header
        header = Label(
            text="User Registration",
            font_size="22sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height="36dp",
            halign="left",
        )
        header.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        content_box.add_widget(header)

        # Instruction subtitle
        sub_header = Label(
            text="Enter details and choose 1 to 4 biometric categories to scan.",
            font_size="13sp",
            color=COLOR_TEXT_MUTED,
            size_hint_y=None,
            height="24dp",
            halign="left",
        )
        sub_header.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        content_box.add_widget(sub_header)

        # Input Card
        input_card = CardBox(size_hint_y=None)
        input_card.bind(minimum_height=input_card.setter("height"))

        lbl_name = Label(
            text="Full Name *",
            font_size="13sp",
            bold=True,
            color=COLOR_TEXT_PRIMARY,
            size_hint_y=None,
            height="20dp",
            halign="left",
        )
        lbl_name.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        input_card.add_widget(lbl_name)

        self.input_name = StyledTextInput(hint_text="e.g. Ahmed Ali")
        input_card.add_widget(self.input_name)

        lbl_id = Label(
            text="User ID *",
            font_size="13sp",
            bold=True,
            color=COLOR_TEXT_PRIMARY,
            size_hint_y=None,
            height="20dp",
            halign="left",
        )
        lbl_id.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        input_card.add_widget(lbl_id)

        self.input_user_id = StyledTextInput(hint_text="e.g. U-1024")
        input_card.add_widget(self.input_user_id)

        content_box.add_widget(input_card)

        # Biometrics Selection Card
        cat_card = CardBox(size_hint_y=None)
        cat_card.bind(minimum_height=cat_card.setter("height"))

        lbl_cat_title = Label(
            text="Select Biometric Categories (1 - 4)",
            font_size="14sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height="24dp",
            halign="left",
        )
        lbl_cat_title.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        cat_card.add_widget(lbl_cat_title)

        self.check_items = {}
        for cat in BIOMETRIC_CATEGORIES:
            item = BiometricCheckItem(cat, BIOMETRIC_LABELS[cat])
            self.check_items[cat] = item
            cat_card.add_widget(item)

        content_box.add_widget(cat_card)

        # Validation feedback label
        self.lbl_feedback = Label(
            text="",
            font_size="13sp",
            color=COLOR_DANGER,
            size_hint_y=None,
            height="24dp",
            halign="center",
        )
        self.lbl_feedback.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        content_box.add_widget(self.lbl_feedback)

        # Action Buttons
        btn_start = PrimaryButton(text="START CAPTURE")
        btn_start.bind(on_release=self._start_capture)
        content_box.add_widget(btn_start)

        btn_cancel = SecondaryButton(text="Back to Home")
        btn_cancel.bind(on_release=self._go_home)
        content_box.add_widget(btn_cancel)

        scroll.add_widget(content_box)
        self.add_widget(scroll)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_pre_enter(self):
        """Clear errors when entering screen."""
        self.lbl_feedback.text = ""

    def _go_home(self, *args):
        self.manager.current = "home"

    def _start_capture(self, *args):
        name = self.input_name.text.strip()
        user_id = self.input_user_id.text.strip()

        if not name:
            self.lbl_feedback.text = "Enter user name."
            return

        if not user_id:
            self.lbl_feedback.text = "Enter User ID."
            return

        selected_cats = [
            cat for cat, item in self.check_items.items() if item.is_checked
        ]

        if not selected_cats:
            self.lbl_feedback.text = "Select at least one biometric type."
            return

        # Check existing user and biometric records in database
        from app.services.database import get_user, biometric_exists
        existing_user = get_user(user_id)

        cats_to_capture = []
        already_registered_cats = []

        if existing_user:
            for cat in selected_cats:
                if biometric_exists(user_id, cat):
                    already_registered_cats.append(BIOMETRIC_LABELS.get(cat, cat))
                else:
                    cats_to_capture.append(cat)

            if already_registered_cats and not cats_to_capture:
                self.lbl_feedback.text = f"Already registered for {user_id}:\n" + ", ".join(already_registered_cats)
                return
            elif already_registered_cats:
                self.lbl_feedback.text = f"Skipping registered: {', '.join(already_registered_cats)}"
        else:
            cats_to_capture = selected_cats

        # Prepare capture queue and pass to camera_capture screen
        cam_screen = self.manager.get_screen("camera_capture")
        cam_screen.setup_registration_flow(
            user_id=user_id,
            name=name,
            categories_to_capture=cats_to_capture,
        )
        self.manager.current = "camera_capture"
