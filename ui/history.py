"""History view: scrollable list of past downloads."""
import os
import subprocess
import sys

import customtkinter as ctk

import data
from ui import messages, theme


def _open_path(path, reveal=False):
    """Open a file, or reveal its folder, with the OS default handler."""
    target = os.path.dirname(path) if reveal else path
    if sys.platform == "win32":
        os.startfile(target)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


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
            header, text="Clear", width=84, height=34, **theme.BTN_DANGER,
            font=theme.BODY, command=self._clear,
        ).grid(row=0, column=1, sticky="e")

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=1, column=0, sticky="nsew")
        self.list.grid_columnconfigure(0, weight=1)

    def on_show(self):
        for w in self.list.winfo_children():
            w.destroy()
        rows = data.get_history()
        if not rows:
            empty = ctk.CTkFrame(self.list, fg_color="transparent")
            empty.grid(row=0, column=0, pady=36)
            ctk.CTkLabel(empty, text="↻", font=(theme.FONT, 34),
                         text_color=theme.TEXT_FAINT).pack()
            ctk.CTkLabel(empty, text=messages.empty_history(),
                         text_color=theme.TEXT_DIM, font=theme.BODY,
                         ).pack(pady=(6, 0))
            return
        for i, (title, url, filepath, quality, when) in enumerate(rows):
            self._row(i, title, filepath, quality, when)

    def _row(self, i, title, filepath, quality, when):
        card = ctk.CTkFrame(self.list, fg_color=theme.CARD, corner_radius=12,
                            border_width=1, border_color=theme.BORDER_SOFT)
        card.grid(row=i, column=0, sticky="ew", pady=5)
        card.grid_columnconfigure(0, weight=1)
        card.bind("<Enter>",
                  lambda _: card.configure(fg_color=theme.CARD_HOVER))
        card.bind("<Leave>", lambda _: card.configure(fg_color=theme.CARD))

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
                card, text="Play", width=70, height=32, **theme.BTN_PRIMARY,
                font=theme.SMALL,
                command=lambda p=filepath: _open_path(p),
            ).grid(row=0, column=1, rowspan=2, padx=(16, 0))
            ctk.CTkButton(
                card, text="Open folder", width=104, height=32,
                **theme.BTN_GHOST, font=theme.SMALL,
                command=lambda p=filepath: _open_path(p, reveal=True),
            ).grid(row=0, column=2, rowspan=2, padx=(8, 16))

    def _clear(self):
        data.clear_history()
        self.on_show()
