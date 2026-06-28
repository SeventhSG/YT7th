"""Main window with left sidebar navigation."""
import os
import sys

import customtkinter as ctk
from PIL import Image

from ui import theme
from ui.home import HomeView
from ui.history import HistoryView
from ui.settings import SettingsView

ctk.set_appearance_mode("dark")


def asset_path(name):
    """Resolve an asset path in dev and inside a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, "assets", name)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT7th")
        self.geometry("960x640")
        self.minsize(820, 560)
        self.configure(fg_color=theme.BG)

        ico = asset_path("logo.ico")
        if os.path.exists(ico):
            try:
                self.iconbitmap(ico)
            except Exception:  # noqa: BLE001
                pass

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

        self.views = {
            "home": HomeView(self),
            "history": HistoryView(self),
            "settings": SettingsView(self),
        }
        for v in self.views.values():
            v.grid(row=0, column=1, sticky="nsew", padx=36, pady=32)
            v.grid_remove()

        self.show("home")

    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, width=104, corner_radius=0, fg_color=theme.SIDEBAR)
        bar.grid(row=0, column=0, sticky="nsew")
        bar.grid_propagate(False)

        # Logo mark, no wordmark
        logo_path = asset_path("logo.png")
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            self.logo_img = ctk.CTkImage(img, size=(46, 46))
            ctk.CTkLabel(bar, image=self.logo_img, text="").pack(pady=(26, 30))
        else:
            ctk.CTkLabel(bar, text="7", font=(theme.FONT, 28, "bold"),
                         text_color=theme.ACCENT).pack(pady=(26, 30))

        self.nav_buttons = {}
        items = [("home", "Home", "⌂"),
                 ("history", "History", "↻"),
                 ("settings", "Settings", "⚙")]
        for key, label, icon in items:
            btn = ctk.CTkButton(
                bar, text=f"{icon}\n{label}", width=84, height=58,
                corner_radius=14, fg_color="transparent",
                hover_color=theme.CARD_HOVER, text_color=theme.TEXT_DIM,
                font=(theme.FONT, 12), command=lambda k=key: self.show(k),
            )
            btn.pack(pady=5, padx=10)
            self.nav_buttons[key] = btn

    def show(self, key):
        for v in self.views.values():
            v.grid_remove()
        self.views[key].grid()
        if hasattr(self.views[key], "on_show"):
            self.views[key].on_show()
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=theme.ACCENT_SOFT, text_color=theme.TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=theme.TEXT_DIM)


def run():
    App().mainloop()
