"""Main window with left sidebar navigation."""
import os

import customtkinter as ctk
from PIL import Image

from version import __version__
from resources import resource_path
from ui import theme
from ui.home import HomeView
from ui.history import HistoryView
from ui.settings import SettingsView

ctk.set_appearance_mode("dark")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"YT7th {__version__}")
        self.geometry("960x640")
        self.minsize(820, 560)
        self.configure(fg_color=theme.BG)

        ico = resource_path("assets", "logo.ico")
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
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, width=104, corner_radius=0, fg_color=theme.SIDEBAR)
        bar.grid(row=0, column=0, sticky="nsew")
        bar.grid_propagate(False)

        # Logo mark, no wordmark
        logo_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            self.logo_img = ctk.CTkImage(img, size=(46, 46))
            ctk.CTkLabel(bar, image=self.logo_img, text="").pack(pady=(26, 30))
        else:
            ctk.CTkLabel(bar, text="7", font=(theme.FONT, 28, "bold"),
                         text_color=theme.ACCENT).pack(pady=(26, 30))

        self.nav_buttons = {}
        self.nav_marks = {}
        items = [("home", "Home", "⌂"),
                 ("history", "History", "↻"),
                 ("settings", "Settings", "⚙")]
        for key, label, icon in items:
            row = ctk.CTkFrame(bar, fg_color="transparent")
            row.pack(pady=5, padx=4, fill="x")
            mark = ctk.CTkFrame(row, width=3, height=44, corner_radius=2,
                                fg_color=theme.SIDEBAR)
            mark.pack(side="left", padx=(0, 3))
            btn = ctk.CTkButton(
                row, text=f"{icon}\n{label}", width=84, height=58,
                corner_radius=14, fg_color="transparent",
                hover_color=theme.CARD_HOVER, text_color=theme.TEXT_DIM,
                font=(theme.FONT, 12), command=lambda k=key: self.show(k),
            )
            btn.pack(side="left")
            self.nav_buttons[key] = btn
            self.nav_marks[key] = mark

        ctk.CTkLabel(bar, text=f"v{__version__}", font=theme.SMALL,
                     text_color=theme.TEXT_FAINT).pack(side="bottom", pady=14)

    def show(self, key):
        for v in self.views.values():
            v.grid_remove()
        self.views[key].grid()
        if hasattr(self.views[key], "on_show"):
            self.views[key].on_show()
        for k, btn in self.nav_buttons.items():
            active = k == key
            btn.configure(
                fg_color=theme.ACCENT_SOFT if active else "transparent",
                text_color=theme.TEXT if active else theme.TEXT_DIM)
            self.nav_marks[k].configure(
                fg_color=theme.ACCENT if active else theme.SIDEBAR)

    def _on_close(self):
        self.views["home"].queue.shutdown()
        self.destroy()


def run():
    App().mainloop()
