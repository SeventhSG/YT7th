"""Settings view: download folder and authentication."""
import webbrowser
from tkinter import filedialog

import customtkinter as ctk

import data
from auth import SUPPORTED_BROWSERS, browser_running
from ui import theme


class SettingsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.settings = data.load_settings()
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Settings", font=theme.H1, text_color=theme.TEXT,
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Download folder
        folder_card = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=16,
                                   border_width=1, border_color=theme.BORDER)
        folder_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        folder_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            folder_card, text="Download folder", font=(theme.FONT, 13, "bold"),
            text_color=theme.TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        self.folder_label = ctk.CTkLabel(
            folder_card, text=self.settings["download_dir"],
            font=(theme.FONT, 12), text_color=theme.TEXT_DIM, anchor="w",
        )
        self.folder_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        ctk.CTkButton(
            folder_card, text="Change", width=104, height=36, corner_radius=10,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, font=theme.BODY,
            command=self._pick_folder,
        ).grid(row=0, column=1, rowspan=2, padx=16)

        # Authentication
        auth_card = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=16,
                                 border_width=1, border_color=theme.BORDER)
        auth_card.grid(row=2, column=0, sticky="ew")
        auth_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            auth_card, text="Account access",
            font=(theme.FONT, 13, "bold"), text_color=theme.TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            auth_card,
            text="To archive member-only or private videos you have access to, "
                 "give YT7th your login cookies. Personal archival use only.",
            font=(theme.FONT, 11), text_color=theme.TEXT_DIM, anchor="w",
            wraplength=600, justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 12))

        # Method 1: cookies.txt file (recommended)
        ctk.CTkLabel(
            auth_card, text="COOKIES FILE  (recommended)",
            font=(theme.FONT, 10, "bold"), text_color=theme.TEXT_FAINT, anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=16)
        ctk.CTkLabel(
            auth_card,
            text="Export a cookies.txt with a browser extension such as "
                 "\"Get cookies.txt LOCALLY\", then select it here. Works even "
                 "while the browser is open.",
            font=(theme.FONT, 11), text_color=theme.TEXT_DIM, anchor="w",
            wraplength=600, justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 6))

        self.cookies_label = ctk.CTkLabel(
            auth_card, text=self.settings.get("cookies_file") or "No file selected",
            font=(theme.FONT, 11), text_color=theme.TEXT_DIM, anchor="w",
        )
        self.cookies_label.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 6))

        file_row = ctk.CTkFrame(auth_card, fg_color="transparent")
        file_row.grid(row=5, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 14))
        ctk.CTkButton(
            file_row, text="Choose file", width=110, height=34, corner_radius=10,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, font=theme.BODY,
            command=self._pick_cookies,
        ).pack(side="left")
        ctk.CTkButton(
            file_row, text="Clear", width=70, height=34, corner_radius=10,
            fg_color=theme.ELEVATED, hover_color=theme.CARD_HOVER, font=theme.BODY,
            command=self._clear_cookies,
        ).pack(side="left", padx=8)

        # Method 2: browser cookies
        ctk.CTkLabel(
            auth_card, text="OR READ FROM BROWSER",
            font=(theme.FONT, 10, "bold"), text_color=theme.TEXT_FAINT, anchor="w",
        ).grid(row=6, column=0, sticky="w", padx=16)
        ctk.CTkLabel(
            auth_card,
            text="Close the browser completely first, or this will fail "
                 "(the browser locks its cookie database while running).",
            font=(theme.FONT, 11), text_color=theme.TEXT_DIM, anchor="w",
            wraplength=600, justify="left",
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 6))

        self.browser = ctk.CTkOptionMenu(
            auth_card, values=SUPPORTED_BROWSERS, fg_color=theme.ELEVATED,
            button_color=theme.ACCENT, button_hover_color=theme.ACCENT_HOVER,
            width=160, corner_radius=10, font=theme.BODY,
            command=lambda _: self._save(),
        )
        self.browser.set(self.settings.get("cookies_browser", "none"))
        self.browser.grid(row=8, column=0, sticky="w", padx=16, pady=(0, 6))

        self.browser_warn = ctk.CTkLabel(
            auth_card, text="", font=(theme.FONT, 11), text_color=theme.DANGER,
            anchor="w", wraplength=600, justify="left",
        )
        self.browser_warn.grid(row=9, column=0, columnspan=2, sticky="w",
                               padx=16, pady=(0, 16))

        self.saved = ctk.CTkLabel(
            self, text="", font=(theme.FONT, 12), text_color=theme.ACCENT,
        )
        self.saved.grid(row=3, column=0, sticky="w", pady=12)

        # Footer credit
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="w", pady=(8, 0))
        ctk.CTkLabel(footer, text="Developed by ", font=theme.SMALL,
                     text_color=theme.TEXT_DIM).pack(side="left")
        link = ctk.CTkLabel(footer, text="SeventhSG", font=(theme.FONT, 11, "bold"),
                            text_color=theme.ACCENT, cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>",
                  lambda _: webbrowser.open("https://github.com/SeventhSG"))

        self._update_browser_warn()

    def on_show(self):
        self._update_browser_warn()

    def _pick_cookies(self):
        path = filedialog.askopenfilename(
            title="Select cookies.txt",
            filetypes=[("Cookies file", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.settings["cookies_file"] = path
            self.cookies_label.configure(text=path)
            self._save()

    def _clear_cookies(self):
        self.settings["cookies_file"] = ""
        self.cookies_label.configure(text="No file selected")
        self._save()

    def _update_browser_warn(self):
        b = self.browser.get()
        if b != "none" and browser_running(b):
            self.browser_warn.configure(
                text=f"{b.capitalize()} is running. Close it fully before "
                     "downloading, or use a cookies.txt file instead.")
        else:
            self.browser_warn.configure(text="")

    def _pick_folder(self):
        path = filedialog.askdirectory(initialdir=self.settings["download_dir"])
        if path:
            self.settings["download_dir"] = path
            self.folder_label.configure(text=path)
            self._save()

    def _save(self):
        self.settings["cookies_browser"] = self.browser.get()
        data.save_settings(self.settings)
        self._update_browser_warn()
        self.saved.configure(text="Saved")
        self.after(1500, lambda: self.saved.configure(text=""))
