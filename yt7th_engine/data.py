"""Settings (JSON) and download history (SQLite)."""
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def app_data_dir():
    """Per-user app-data directory, following each OS's convention."""
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "YT7th"


APP_DIR = app_data_dir()
APP_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_PATH = APP_DIR / "settings.json"
HISTORY_PATH = APP_DIR / "history.db"

DEFAULT_SETTINGS = {
    "download_dir": str(Path.home() / "Downloads" / "YT7th"),
    "quality": "1080p",
    "format": "MP4",
    "audio_only": False,
    "subtitles": False,
    "cookies_browser": "none",  # none, chrome, firefox, edge, brave
    "cookies_file": "",         # path to a Netscape cookies.txt (recommended)
}


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2), encoding="utf-8"
    )


def _connect():
    conn = sqlite3.connect(HISTORY_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT,
            filepath TEXT,
            quality TEXT,
            downloaded_at TEXT
        )"""
    )
    return conn


def add_history(title, url, filepath, quality):
    conn = _connect()
    conn.execute(
        "INSERT INTO history (title, url, filepath, quality, downloaded_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, url, filepath, quality, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def get_history(limit=200):
    conn = _connect()
    rows = conn.execute(
        "SELECT title, url, filepath, quality, downloaded_at "
        "FROM history ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def clear_history():
    conn = _connect()
    conn.execute("DELETE FROM history")
    conn.commit()
    conn.close()
