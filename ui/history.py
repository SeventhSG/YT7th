"""History view: scrollable list of past downloads."""
import os
import subprocess

import customtkinter as ctk

import data
from ui import messages, theme


class HistoryView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="History", font=theme.H1, text_color=theme.TEXT,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="Clear", width=84, height=34, corner_radius=10,
            fg_color=theme.CARD, hover_color=theme.ACCENT,
            border_width=1, border_color=theme.BORDER, font=theme.BODY,
            command=self._clear,
        ).grid(row=0, column=1, sticky="e")

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=1, column=0, sticky="nsew")
        self.list.grid_columnconfigure(0, weight=1)

    def on_show(self):
        for w in self.list.winfo_children():
            w.destroy()
        rows = data.get_history()
        if not rows:
            ctk.CTkLabel(
                self.list, text=messages.empty_history(),
                text_color=theme.TEXT_DIM, font=theme.BODY,
            ).grid(row=0, column=0, pady=24)
            return
        for i, (title, url, filepath, quality, when) in enumerate(rows):
            self._row(i, title, filepath, quality, when)

    def _row(self, i, title, filepath, quality, when):
        card = ctk.CTkFrame(self.list, fg_color=theme.CARD, corner_radius=12,
                            border_width=1, border_color=theme.BORDER_SOFT)
        card.grid(row=i, column=0, sticky="ew", pady=5)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=title[:70], font=theme.H2,
            text_color=theme.TEXT, anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))

        ctk.CTkLabel(
            card, text=f"{quality}   -   {when}", font=theme.SMALL,
            text_color=theme.TEXT_DIM, anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 12))

        if filepath and os.path.exists(filepath):
            ctk.CTkButton(
                card, text="Open folder", width=104, height=32, corner_radius=10,
                fg_color=theme.ELEVATED, hover_color=theme.ACCENT, font=theme.SMALL,
                command=lambda p=filepath: self._open(p),
            ).grid(row=0, column=1, rowspan=2, padx=16)

    def _open(self, filepath):
        folder = os.path.dirname(filepath)
        if os.path.isdir(folder):
            subprocess.Popen(["explorer", folder])

    def _clear(self):
        data.clear_history()
        self.on_show()
