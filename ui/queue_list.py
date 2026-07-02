"""Scrollable list of queue item cards: thumbnail, title, progress, remove."""
import io
import threading
import urllib.request

import customtkinter as ctk
from PIL import Image

from ui import messages, theme

THUMB_SIZE = (96, 54)

STATUS_TEXT = {
    "fetching": "Fetching info...",
    "queued": "Queued",
    "done": messages.DONE[0],
    "cancelled": "Cancelled",
}
STATUS_COLOR = {
    "downloading": theme.TEXT,
    "done": theme.SUCCESS,
    "error": theme.DANGER,
}


def _fmt_duration(seconds):
    if not seconds:
        return ""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _fmt_eta(seconds):
    if not seconds:
        return ""
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s left" if m else f"{s}s left"


class QueueList(ctk.CTkScrollableFrame):
    """Renders QueueItems. All upsert() calls must come from the UI thread."""

    def __init__(self, master, on_remove):
        super().__init__(master, fg_color="transparent")
        self.on_remove = on_remove
        self.grid_columnconfigure(0, weight=1)
        self._cards = {}   # item.id -> dict of widgets
        self._row = 0
        self._empty = ctk.CTkLabel(
            self, text=messages.READY, text_color=theme.TEXT_FAINT,
            font=theme.BODY,
        )
        self._empty.grid(row=0, column=0, pady=28)

    def upsert(self, item):
        if item.status == "cancelled":
            self._drop(item.id)
            return
        card = self._cards.get(item.id) or self._build(item)
        self._refresh(card, item)

    def _drop(self, item_id):
        card = self._cards.pop(item_id, None)
        if card:
            card["frame"].destroy()
        if not self._cards:
            self._empty.grid()

    def _build(self, item):
        self._empty.grid_remove()
        frame = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=12,
                             border_width=1, border_color=theme.BORDER_SOFT)
        self._row += 1
        frame.grid(row=self._row, column=0, sticky="ew", pady=5)
        frame.grid_columnconfigure(1, weight=1)

        thumb = ctk.CTkLabel(frame, text="▶", width=THUMB_SIZE[0],
                             height=THUMB_SIZE[1], fg_color=theme.ELEVATED,
                             corner_radius=8, font=(theme.FONT, 18),
                             text_color=theme.TEXT_FAINT)
        thumb.grid(row=0, column=0, rowspan=3, padx=(12, 14), pady=12)

        title = ctk.CTkLabel(frame, text="", font=(theme.FONT, 14, "bold"),
                             text_color=theme.TEXT, anchor="w")
        title.grid(row=0, column=1, sticky="ew", pady=(12, 0))

        meta = ctk.CTkLabel(frame, text="", font=theme.SMALL,
                            text_color=theme.TEXT_DIM, anchor="w")
        meta.grid(row=1, column=1, sticky="ew")

        detail = ctk.CTkLabel(frame, text="", font=theme.SMALL,
                              text_color=theme.TEXT_FAINT, anchor="w",
                              wraplength=460, justify="left")
        detail.grid(row=2, column=1, sticky="ew", pady=(0, 10))

        bar = ctk.CTkProgressBar(frame, height=6, corner_radius=4,
                                 progress_color=theme.ACCENT,
                                 fg_color=theme.ELEVATED)
        bar.set(0)  # gridded only while downloading

        ctk.CTkButton(
            frame, text="✕", width=30, height=30, font=(theme.FONT, 13),
            fg_color="transparent", hover_color=theme.ACCENT_SOFT,
            text_color=theme.TEXT_DIM, corner_radius=8,
            command=lambda: self.on_remove(item.id),
        ).grid(row=0, column=2, rowspan=3, padx=(8, 12))

        card = {"frame": frame, "thumb": thumb, "title": title, "meta": meta,
                "detail": detail, "bar": bar, "thumb_loaded": False}
        self._cards[item.id] = card
        return card

    def _refresh(self, card, item):
        m = item.metadata
        card["title"].configure(
            text=(m.get("title") or item.url)[:70])

        chip = f"{item.settings.get('format', '')}"
        if not item.settings.get("audio_only"):
            chip = f"{item.settings.get('quality', '')} {chip}"
        bits = [chip.strip()]
        if m.get("is_playlist"):
            bits.append(f"{m['entry_count']} videos")
        elif m.get("duration"):
            bits.append(_fmt_duration(m["duration"]))
        if m.get("channel"):
            bits.append(m["channel"])
        card["meta"].configure(text="   ·   ".join(b for b in bits if b))

        if m.get("thumbnail_url") and not card["thumb_loaded"]:
            card["thumb_loaded"] = True
            threading.Thread(target=self._load_thumb,
                             args=(item.id, m["thumbnail_url"]),
                             daemon=True).start()

        status, p = item.status, item.progress
        if status == "downloading":
            card["bar"].grid(row=3, column=0, columnspan=3, sticky="ew",
                             padx=12, pady=(0, 12))
            card["bar"].set((p.get("percent") or 0) / 100)
            bits = [f"{p.get('percent', 0):.0f}%"]
            if p.get("speed"):
                bits.append(f"{p['speed'] / 1_000_000:.1f} MB/s")
            if p.get("eta"):
                bits.append(_fmt_eta(p["eta"]))
            text = "   -   ".join(bits)
            if p.get("status") == "processing":
                text = "Merging and processing..."
            card["detail"].configure(text=text, text_color=theme.TEXT)
        else:
            card["bar"].grid_remove()
            text = item.error if status == "error" else STATUS_TEXT[status]
            card["detail"].configure(
                text=text, text_color=STATUS_COLOR.get(status, theme.TEXT_FAINT))

    def _load_thumb(self, item_id, url):
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                raw = resp.read()
            img = Image.open(io.BytesIO(raw))
        except Exception:  # noqa: BLE001
            return
        def apply():
            card = self._cards.get(item_id)
            if card:
                card["img"] = ctk.CTkImage(img, size=THUMB_SIZE)
                card["thumb"].configure(image=card["img"], text="")
        self.after(0, apply)
