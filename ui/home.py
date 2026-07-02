"""Home view: URL input, options, and the download queue."""
import webbrowser

import customtkinter as ctk

import data
import updater
from downloader import QUALITY_MAP
from queue_manager import QueueManager
from ui import theme
from ui.queue_list import QueueList

VIDEO_FORMATS = ["MP4", "MKV", "WEBM"]
AUDIO_FORMATS = ["MP3", "M4A"]


class HomeView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.settings = data.load_settings()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # Header
        ctk.CTkLabel(self, text="Download", font=theme.H1,
                     text_color=theme.TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(self, text="Paste a link to archive a video or playlist.",
                     font=theme.BODY, text_color=theme.TEXT_DIM,
                     ).grid(row=1, column=0, sticky="w", pady=(2, 22))

        # URL card
        url_card = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=16,
                                border_width=1, border_color=theme.BORDER)
        url_card.grid(row=2, column=0, sticky="ew")
        url_card.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_card, placeholder_text="https://youtube.com/watch?v=...",
            height=46, font=(theme.FONT, 14), fg_color=theme.ELEVATED,
            border_color=theme.BORDER, corner_radius=10,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(16, 10), pady=16)
        self.url_entry.bind("<Return>", lambda _: self._add())
        self.url_entry.bind(
            "<FocusIn>",
            lambda _: self.url_entry.configure(border_color=theme.ACCENT))
        self.url_entry.bind(
            "<FocusOut>",
            lambda _: self.url_entry.configure(border_color=theme.BORDER))

        self.dl_btn = ctk.CTkButton(
            url_card, text="Download", width=130, height=46,
            **theme.BTN_PRIMARY, font=(theme.FONT, 14, "bold"),
            command=self._add,
        )
        self.dl_btn.grid(row=0, column=1, padx=(0, 16))

        self.url_hint = ctk.CTkLabel(url_card, text="", font=theme.SMALL,
                                     text_color=theme.DANGER, anchor="w")
        # gridded only when a hint is shown

        # Options card
        opts = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=16,
                            border_width=1, border_color=theme.BORDER)
        opts.grid(row=3, column=0, sticky="ew", pady=18)
        opts.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(opts, text="QUALITY", text_color=theme.TEXT_FAINT,
                     font=(theme.FONT, 10, "bold")).grid(
            row=0, column=0, padx=(18, 8), pady=(18, 4), sticky="w")
        ctk.CTkLabel(opts, text="FORMAT", text_color=theme.TEXT_FAINT,
                     font=(theme.FONT, 10, "bold")).grid(
            row=0, column=2, padx=(0, 8), pady=(18, 4), sticky="w")

        self.quality = ctk.CTkOptionMenu(
            opts, values=list(QUALITY_MAP.keys()), fg_color=theme.ELEVATED,
            button_color=theme.ACCENT, button_hover_color=theme.ACCENT_HOVER,
            width=140, corner_radius=10, font=theme.BODY,
        )
        self.quality.set(self.settings.get("quality", "1080p"))
        self.quality.grid(row=1, column=0, columnspan=2, sticky="w",
                          padx=(18, 16), pady=(0, 18))

        self.fmt = ctk.CTkOptionMenu(
            opts, values=VIDEO_FORMATS, fg_color=theme.ELEVATED,
            button_color=theme.ACCENT, button_hover_color=theme.ACCENT_HOVER,
            width=140, corner_radius=10, font=theme.BODY,
        )
        self.fmt.set(self.settings.get("format", "MP4"))
        self.fmt.grid(row=1, column=2, columnspan=2, sticky="w", pady=(0, 18))

        self.audio_var = ctk.BooleanVar(value=self.settings.get("audio_only", False))
        ctk.CTkCheckBox(
            opts, text="Audio only", variable=self.audio_var,
            command=self._toggle_audio, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, text_color=theme.TEXT,
            font=theme.BODY, corner_radius=6,
        ).grid(row=2, column=0, columnspan=2, padx=18, pady=(0, 18), sticky="w")

        self.subs_var = ctk.BooleanVar(value=self.settings.get("subtitles", False))
        ctk.CTkCheckBox(
            opts, text="Include subtitles", variable=self.subs_var,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.TEXT, font=theme.BODY, corner_radius=6,
        ).grid(row=2, column=2, columnspan=2, pady=(0, 18), sticky="w")

        # Queue
        self.queue_list = QueueList(self, on_remove=self._remove_item)
        self.queue_list.grid(row=4, column=0, sticky="nsew")

        self.queue = QueueManager(
            on_update=self._on_item_update,
            on_file_done=data.add_history,
        )

        # Update banner (hidden until a newer release is found)
        self.update_bar = ctk.CTkFrame(self, fg_color=theme.ACCENT_SOFT,
                                       corner_radius=12, border_width=1,
                                       border_color=theme.ACCENT)
        self.update_bar.grid_columnconfigure(0, weight=1)
        self.update_msg = ctk.CTkLabel(
            self.update_bar, text="", text_color=theme.TEXT,
            font=theme.BODY, anchor="w",
        )
        self.update_msg.grid(row=0, column=0, sticky="w", padx=14, pady=8)
        self.update_btn = ctk.CTkButton(
            self.update_bar, text="Download", width=100, height=30,
            **theme.BTN_PRIMARY, font=(theme.FONT, 12, "bold"),
        )
        self.update_btn.grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(
            self.update_bar, text="✕", width=30, height=30, corner_radius=8,
            fg_color="transparent", hover_color=theme.CARD_HOVER,
            text_color=theme.TEXT_DIM, font=(theme.FONT, 13),
            command=self.update_bar.grid_remove,
        ).grid(row=0, column=2, padx=(0, 10), pady=8)
        self.update_bar.grid(row=5, column=0, sticky="ew", pady=(18, 0))
        self.update_bar.grid_remove()

        updater.check_async(self._on_update_check)

        self._toggle_audio()

    def _on_update_check(self, result):
        if not result:
            return

        def show():
            self.update_msg.configure(
                text=f"YT7th {result['version']} is available.")
            self.update_btn.configure(
                command=lambda: webbrowser.open(result["url"]))
            self.update_bar.grid()
        self.after(0, show)

    def _toggle_audio(self):
        if self.audio_var.get():
            self.fmt.configure(values=AUDIO_FORMATS)
            if self.fmt.get() not in AUDIO_FORMATS:
                self.fmt.set("MP3")
            self.quality.configure(state="disabled")
        else:
            self.fmt.configure(values=VIDEO_FORMATS)
            if self.fmt.get() not in VIDEO_FORMATS:
                self.fmt.set("MP4")
            self.quality.configure(state="normal")

    def _current_settings(self):
        s = data.load_settings()
        s["quality"] = self.quality.get()
        s["format"] = self.fmt.get()
        s["audio_only"] = self.audio_var.get()
        s["subtitles"] = self.subs_var.get()
        return s

    def _add(self):
        url = self.url_entry.get().strip()
        if not url:
            self._hint("Please paste a URL first.")
            return
        self._hint("")
        self.queue.add(url, self._current_settings())
        self.url_entry.delete(0, "end")

    def _hint(self, text):
        if text:
            self.url_hint.configure(text=text)
            self.url_hint.grid(row=1, column=0, columnspan=2, sticky="ew",
                               padx=16, pady=(0, 10))
        else:
            self.url_hint.grid_remove()

    def _remove_item(self, item_id):
        self.queue.remove(item_id)

    def _on_item_update(self, item):
        # Fires on worker threads; marshal to the UI thread.
        self.after(0, lambda: self.queue_list.upsert(item))
