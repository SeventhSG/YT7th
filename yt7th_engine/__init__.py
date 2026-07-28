"""YT7th download engine: UI-agnostic core shared by the desktop app and the
editor-host plugins (DaVinci Resolve, Premiere, ...).

Re-exports the stable surface so callers can `from yt7th_engine import ...`.
"""
from . import auth, data, downloader, resources
from .downloader import QUALITY_MAP, AUDIO_CODECS, Downloader, fetch_info, friendly_error
from .queue_manager import QueueManager, QueueItem

__all__ = [
    "auth", "data", "downloader", "resources",
    "QUALITY_MAP", "AUDIO_CODECS", "Downloader", "fetch_info", "friendly_error",
    "QueueManager", "QueueItem",
]
