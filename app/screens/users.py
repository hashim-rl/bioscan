"""
Users Management Screen for BioScan.
Displays registered users and allows deletion of test identities for demo resets.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line

from app.utils.constants import (
    COLOR_BG,
    COLOR_SURFACE,
    COLOR_PRIMARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_BORDER,
    COLOR_DANGER,
    BIOMETRIC_LABELS,
)
from app.screens.widgets import PrimaryButton, SecondaryButton, DangerButton, CardBox


class UserCardItem(Button):
    """Clickable card displaying user summary."""
    def __init__(self, user_info: dict, on_tap_callback, **kwargs):
        super().__init__(**kwargs)
        self.user_info = user_info
        self.on_tap_callback = on_tap_callback

        self.background_color = (0, 0, 0, 0)
        self.background_normal = ""
        self.size_hint_y = None
        self.height = "76dp"

        with self.canvas.before:
            Color(*COLOR_SURFACE)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
            Color(*COLOR_BORDER)
            self.line = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 8], width=1.1)

        self.bind(pos=self._update_rect, size=self._update_rect)

        # Internal layout
        box = BoxLayout(
            orientation="vertical",
            padding=["12dp", "8dp", "12dp", "8dp"],
            spacing="4dp",
            pos=self.pos,
            size=self.size,
        )
        self.bind(pos=lambda *_: setattr(box, "pos", self.pos), size=lambda *_: setattr(box, "size", self.size))

        name_lbl = Label(
            text=f"{user_info.get('name', 'Unknown')}",
            font_size="15sp",
            bold=True,
            color=COLOR_TEXT_PRIMARY,
            size_hint_y=None,
            height="22dp",
            halign="left",
        )
        name_lbl.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        box.add_widget(name_lbl)

        bio_count = user_info.get("biometric_count", 0)
        sub_lbl = Label(
            text=f"ID: {user_info.get('user_id', '')}  •  {bio_count} Biometric(s)",
            font_size="12sp",
            color=COLOR_TEXT_MUTED,
            size_hint_y=None,
            height="18dp",
            halign="left",
        )
        sub_lbl.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        box.add_widget(sub_lbl)

        self.add_widget(box)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rounded_rectangle = [self.x, self.y, self.width, self.height, 8]

    def on_release(self):
        if self.on_tap_callback:
            self.on_tap_callback(self.user_info)


class UsersScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*COLOR_BG)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        main_box = BoxLayout(
            orientation="vertical",
            padding=["20dp", "24dp", "20dp", "20dp"],
            spacing="14dp",
        )

        # Header
        header = Label(
            text="Registered Users",
            font_size="22sp",
            bold=True,
            color=COLOR_PRIMARY,
            size_hint_y=None,
            height="34dp",
            halign="left",
        )
        header.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        main_box.add_widget(header)

        sub_header = Label(
            text="Tap a user to view registered categories or delete record.",
            font_size="13sp",
            color=COLOR_TEXT_MUTED,
            size_hint_y=None,
            height="22dp",
            halign="left",
        )
        sub_header.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        main_box.add_widget(sub_header)

        # Scrollable list container
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.list_container = BoxLayout(
            orientation="vertical",
            spacing="10dp",
            size_hint_y=None,
        )
        self.list_container.bind(minimum_height=self.list_container.setter("height"))
        scroll.add_widget(self.list_container)
        main_box.add_widget(scroll)

        # Empty state label
        self.lbl_empty = Label(
            text="No users registered in local database.",
            font_size="14sp",
            color=COLOR_TEXT_MUTED,
            size_hint_y=None,
            height="30dp",
            halign="center",
        )
        self.list_container.add_widget(self.lbl_empty)

        # Back button
        btn_back = SecondaryButton(text="Back to Home")
        btn_back.bind(on_release=self._go_home)
        main_box.add_widget(btn_back)

        self.add_widget(main_box)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_pre_enter(self):
        """Refresh user list from database."""
        self.refresh_users()

    def refresh_users(self):
        self.list_container.clear_widgets()

        # Database integration will populate this in Milestone 2
        # For Milestone 1 shell:
        users = []
        try:
            from app.services.database import get_all_users, get_biometrics_for_user
            db_users = get_all_users()
            for u in db_users:
                bios = get_biometrics_for_user(u["user_id"])
                users.append({
                    "user_id": u["user_id"],
                    "name": u["name"],
                    "biometric_count": len(bios),
                    "types": [b["biometric_type"] for b in bios],
                })
        except Exception:
            # Placeholder for initial shell test
            users = []

        if not users:
            self.lbl_empty.text = "No users registered yet.\nTap 'Register New User' to add one."
            self.lbl_empty.size_hint_y = None
            self.lbl_empty.height = "60dp"
            self.list_container.add_widget(self.lbl_empty)
            return

        for user in users:
            card = UserCardItem(user, on_tap_callback=self._show_user_details)
            self.list_container.add_widget(card)

    def _show_user_details(self, user_info: dict):
        """Show popup dialog with user details and delete button."""
        types_text = "\n".join([f"• {BIOMETRIC_LABELS.get(t, t)}" for t in user_info.get("types", [])])
        if not types_text:
            types_text = "None"

        content = BoxLayout(orientation="vertical", spacing="12dp", padding="16dp")

        msg = Label(
            text=(
                f"[b]Name:[/b] {user_info.get('name')}\n"
                f"[b]User ID:[/b] {user_info.get('user_id')}\n\n"
                f"[b]Registered Biometrics:[/b]\n{types_text}"
            ),
            markup=True,
            font_size="13sp",
            color=COLOR_TEXT_PRIMARY,
            halign="left",
        )
        msg.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        content.add_widget(msg)

        btn_box = BoxLayout(spacing="10dp", size_hint_y=None, height="44dp")
        btn_del = DangerButton(text="DELETE USER")
        btn_cancel = SecondaryButton(text="Cancel")

        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_del)
        content.add_widget(btn_box)

        popup = Popup(
            title="User Details",
            content=content,
            size_hint=(0.85, 0.55),
            auto_dismiss=True,
        )

        def do_delete(*_):
            popup.dismiss()
            self._confirm_delete(user_info)

        btn_cancel.bind(on_release=popup.dismiss)
        btn_del.bind(on_release=do_delete)
        popup.open()

    def _confirm_delete(self, user_info: dict):
        """Ask confirmation before permanently removing user and biometrics."""
        content = BoxLayout(orientation="vertical", spacing="12dp", padding="16dp")
        lbl = Label(
            text=f"Permanently delete user '{user_info.get('name')}' ({user_info.get('user_id')}) and all associated biometric records?",
            font_size="13sp",
            color=COLOR_TEXT_PRIMARY,
            halign="center",
        )
        lbl.bind(size=lambda l, sz: setattr(l, "text_size", sz))
        content.add_widget(lbl)

        btn_box = BoxLayout(spacing="10dp", size_hint_y=None, height="44dp")
        btn_yes = DangerButton(text="YES, DELETE")
        btn_no = SecondaryButton(text="NO, KEEP")

        btn_box.add_widget(btn_no)
        btn_box.add_widget(btn_yes)
        content.add_widget(btn_box)

        confirm_popup = Popup(
            title="Confirm Deletion",
            content=content,
            size_hint=(0.85, 0.4),
            auto_dismiss=False,
        )

        def perform_delete(*_):
            confirm_popup.dismiss()
            try:
                from app.services.database import delete_user
                delete_user(user_info.get("user_id"))
            except Exception as e:
                print(f"[BioScan Delete] Error: {e}")
            self.refresh_users()

        btn_no.bind(on_release=confirm_popup.dismiss)
        btn_yes.bind(on_release=perform_delete)
        confirm_popup.open()

    def _go_home(self, *args):
        self.manager.current = "home"
