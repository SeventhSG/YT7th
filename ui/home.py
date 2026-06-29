"""Home view: URL input, options, download with progress and cancel."""
import shutil
import threading
import webbrowser

import customtkinter as ctk

import data
import updater
from downloader import Downloader, QUALITY_MAP
from ui import messages, theme

VIDEO_FORMATS = ["MP4", "MKV", "WEBM"]
AUDIO_FORMATS = ["MP3", "M4A"]
LOW_SPACE_GB = 1.0


class HomeView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.settings = data.load_settings()
        self.downloader = None
        self.grid_columnconfigure(0, weight=1)

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

        self.dl_btn = ctk.CTkButton(
            url_card, text="Download", width=130, height=46, corner_radius=10,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            font=(theme.FONT, 14, "bold"), command=self._start,
        )
        self.dl_btn.grid(row=0, column=1, padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            url_card, text="Cancel", width=90, height=46, corner_radius=10,
            fg_color="transparent", hover_color=theme.ACCENT_SOFT,
            border_width=1, border_color=theme.DANGER, text_color=theme.DANGER,
            font=(theme.FONT, 13, "bold"), command=self._cancel,
        )
        # shown only while downloading

        # Options card
        opts = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=16,
                            border_width=1, border_color=theme.BORDER)
        opts.grid(row=3, column=0, sticky="ew", pady=18)
        opts.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(opts, text="QUALITY", text_color=theme.TEXT_FAINT,
                     font=(theme.FONT, 10, "bold")).grid(
            row=0, column=0, padx=(18, 8), pady=(16, 4), sticky="w")
        ctk.CTkLabel(opts, text="FORMAT", text_color=theme.TEXT_FAINT,
                     font=(theme.FONT, 10, "bold")).grid(
            row=0, column=2, padx=(0, 8), pady=(16, 4), sticky="w")

        self.quality = ctk.CTkOptionMenu(
            opts, values=list(QUALITY_MAP.keys()), fg_color=theme.ELEVATED,
            button_color=theme.ACCENT, button_hover_color=theme.ACCENT_HOVER,
            width=140, corner_radius=10, font=theme.BODY,
        )
        self.quality.set(self.settings.get("quality", "1080p"))
        self.quality.grid(row=1, column=0, columnspan=2, sticky="w",
                          padx=(18, 16), pady=(0, 16))

        self.fmt = ctk.CTkOptionMenu(
            opts, values=VIDEO_FORMATS, fg_color=theme.ELEVATED,
            button_color=theme.ACCENT, button_hover_color=theme.ACCENT_HOVER,
            width=140, corner_radius=10, font=theme.BODY,
        )
        self.fmt.set(self.settings.get("format", "MP4"))
        self.fmt.grid(row=1, column=2, columnspan=2, sticky="w", pady=(0, 16))

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

        # Progress card
        prog_card = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=16,
                                 border_width=1, border_color=theme.BORDER)
        prog_card.grid(row=4, column=0, sticky="ew")
        prog_card.grid_columnconfigure(0, weight=1)

        self.status = ctk.CTkLabel(
            prog_card, text=messages.READY, text_color=theme.TEXT_DIM,
            font=theme.BODY, anchor="w", justify="left", wraplength=560,
        )
        self.status.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        self.progress = ctk.CTkProgressBar(
            prog_card, height=10, corner_radius=6, progress_color=theme.ACCENT,
            fg_color=theme.ELEVATED,
        )
        self.progress.grid(row=1, column=0, sticky="ew", padx=16)
        self.progress.set(0)

        self.detail = ctk.CTkLabel(
            prog_card, text="", text_color=theme.TEXT_FAINT,
            font=theme.SMALL, anchor="w",
        )
        self.detail.grid(row=2, column=0, sticky="ew", padx=16, pady=(6, 14))

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
            corner_radius=8, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, font=(theme.FONT, 12, "bold"),
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

    def _free_gb(self, path):
        try:
            return shutil.disk_usage(path).free / 1_000_000_000
        except OSError:
            return None

    def _start(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status.configure(text="Please paste a URL first.",
                                  text_color=theme.DANGER)
            return
        settings = self._current_settings()
        free = self._free_gb(settings["download_dir"])
        if free is not None and free < LOW_SPACE_GB:
            self.status.configure(
                text=f"Low disk space ({free:.1f} GB free). Merging may fail - "
                     "free up space or change the download folder in Settings.",
                text_color=theme.DANGER,
            )
            return

        self.dl_btn.configure(state="disabled", text="Downloading...")
        self.cancel_btn.grid(row=0, column=2, padx=(0, 16))
        self.progress.set(0)
        self.status.configure(text=messages.starting(), text_color=theme.TEXT_DIM)
        self.detail.configure(text="")
        self.downloader = Downloader(
            progress_cb=self._on_progress, done_cb=self._on_done,
            error_cb=self._on_error,
        )
        threading.Thread(target=self.downloader.download,
                         args=(url, settings), daemon=True).start()

    def _cancel(self):
        if self.downloader:
            self.downloader.cancel()
            self.status.configure(text="Cancelling...", text_color=theme.TEXT_DIM)

    def _reset_buttons(self):
        self.dl_btn.configure(state="normal", text="Download")
        self.cancel_btn.grid_remove()

    @staticmethod
    def _fmt_eta(seconds):
        if not seconds:
            return ""
        m, s = divmod(int(seconds), 60)
        return f"{m}m {s:02d}s left" if m else f"{s}s left"

    def _on_progress(self, p):
        def update():
            self.progress.set(p["percent"] / 100)
            if p["status"] == "processing":
                self.status.configure(text="Merging and processing...",
                                      text_color=theme.TEXT)
                self.detail.configure(text="Almost there")
            else:
                title = p["title"][:60] if p["title"] else "Downloading..."
                self.status.configure(text=title, text_color=theme.TEXT)
                speed = p["speed"] / 1_000_000 if p["speed"] else 0
                eta = self._fmt_eta(p["eta"])
                bits = [f"{p['percent']:.0f}%"]
                if speed:
                    bits.append(f"{speed:.1f} MB/s")
                if eta:
                    bits.append(eta)
                self.detail.configure(text="   -   ".join(bits))
        self.after(0, update)

    def _on_done(self, title, url, filepath, quality):
        data.add_history(title, url, filepath, quality)

        def finish():
            self.progress.set(1)
            self.status.configure(text=messages.done(), text_color=theme.TEXT)
            self.detail.configure(text=title[:70])
            self._reset_buttons()
        self.after(0, finish)

    def _on_error(self, msg):
        def show():
            self._reset_buttons()
            self.progress.set(0)
            if msg == "Cancelled":
                self.status.configure(text="Cancelled. No harm done.",
                                      text_color=theme.TEXT_DIM)
                self.detail.configure(text="")
            else:
                self.status.configure(text=f"⚠  {msg}", text_color=theme.DANGER)
                self.detail.configure(text="")
        self.after(0, show)
