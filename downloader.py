"""yt-dlp download engine with progress callbacks."""
import os
import shutil
from pathlib import Path

import yt_dlp

import resources
from auth import cookie_opts

# JS runtimes yt-dlp can use to solve YouTube's signature/n challenge.
# Without one, YouTube returns only image storyboards. Preference order.
JS_RUNTIME_ORDER = ["deno", "node", "bun"]


def detect_js_runtimes():
    """Return a js_runtimes dict for every runtime found on PATH."""
    return {rt: {} for rt in JS_RUNTIME_ORDER if shutil.which(rt)}

# Each cap falls back to a progressive stream at that height, then to the
# best available, so a video with no match at the chosen height still works.
QUALITY_MAP = {
    "Best": "bestvideo+bestaudio/best",
    "2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best",
    "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
}

AUDIO_CODECS = {"MP3": "mp3", "M4A": "m4a"}

# Error fragments that mean "this needs your account to access".
_AUTH_HINTS = (
    "members-only", "members only", "join this channel",
    "available to this channel", "private video", "sign in to confirm",
    "log in", "login required", "requires payment", "purchase",
    "confirm your age", "age-restricted", "account required",
)


def needs_auth(msg):
    low = msg.lower()
    return any(h in low for h in _AUTH_HINTS)


def friendly_error(msg):
    """Turn a raw yt-dlp error into a short, human message."""
    low = msg.lower()
    if "cookie database" in low:
        return ("Could not read your browser cookies. Close the browser fully, "
                "or export a cookies.txt and pick it in Settings.")
    if not detect_js_runtimes() and (
            "format is not available" in low or "only images" in low):
        return ("No JavaScript runtime found. YT7th needs Node, Deno, or Bun "
                "to fetch video streams. Grab Node.js from nodejs.org and retry.")
    if any(h in low for h in ("members-only", "members only",
                              "join this channel", "available to this channel")):
        return ("This is a members-only video. Add your account cookies in "
                "Settings to archive it.")
    if "private video" in low:
        return "This video is private. You need an account that can view it."
    if "confirm your age" in low or "age-restricted" in low:
        return ("This video is age-restricted. Add your account cookies in "
                "Settings to archive it.")
    if any(k in low for k in ("video unavailable", "no longer available",
                              "has been removed", "this video is not available")):
        return "This video is unavailable. It may be removed or region-locked."
    if "is not a valid url" in low or "unsupported url" in low:
        return "That does not look like a valid video link. Check the URL."
    if "format is not available" in low:
        return "That quality is not available here. Try another quality or 'Best'."
    if any(k in low for k in ("timed out", "connection", "network",
                              "getaddrinfo", "failed to resolve")):
        return "Network hiccup. Check your connection and try again."
    if "ffmpeg" in low:
        return "FFmpeg is needed to merge audio and video. Install it and retry."
    if "no space" in low or "errno 28" in low:
        return "Out of disk space. Free up room or change the download folder."
    return msg.splitlines()[0][:200] if msg else "Something went wrong."


class Downloader:
    """Wraps yt-dlp. Reports progress through a callback.

    progress_cb receives a dict: {status, percent, speed, eta, title}.
    done_cb receives (title, filepath, quality) on each finished file.
    error_cb receives an error message string.
    """

    def __init__(self, progress_cb=None, done_cb=None, error_cb=None):
        self.progress_cb = progress_cb
        self.done_cb = done_cb
        self.error_cb = error_cb
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _hook(self, d):
        if self._cancel:
            raise yt_dlp.utils.DownloadCancelled("Cancelled by user")
        if not self.progress_cb:
            return
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total * 100) if total else 0
            self.progress_cb({
                "status": "downloading",
                "percent": percent,
                "speed": d.get("speed") or 0,
                "eta": d.get("eta") or 0,
                "title": d.get("info_dict", {}).get("title", ""),
            })
        elif status == "finished":
            self.progress_cb({
                "status": "processing",
                "percent": 100,
                "speed": 0,
                "eta": 0,
                "title": d.get("info_dict", {}).get("title", ""),
            })

    def _build_opts(self, settings, use_cookies=False):
        out_dir = settings.get("download_dir")
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        opts = {
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [self._hook],
            "noplaylist": False,
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
        }
        runtimes = detect_js_runtimes()
        if runtimes:
            opts["js_runtimes"] = runtimes

        bundled = resources.bin_dir()
        if os.path.isdir(bundled):
            opts["ffmpeg_location"] = bundled
        if use_cookies:
            opts.update(cookie_opts(settings))

        if settings.get("audio_only"):
            codec = AUDIO_CODECS.get(settings.get("format", "MP3"), "mp3")
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": "0",
            }]
        else:
            opts["format"] = QUALITY_MAP.get(
                settings.get("quality", "1080p"), QUALITY_MAP["1080p"]
            )
            opts["merge_output_format"] = settings.get("format", "MP4").lower()

        if settings.get("subtitles"):
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = True
            opts["subtitleslangs"] = ["en"]

        return opts

    def _run(self, url, settings, use_cookies):
        opts = self._build_opts(settings, use_cookies=use_cookies)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return
            entries = info.get("entries") or [info]
            quality = (
                settings.get("format", "MP3")
                if settings.get("audio_only")
                else settings.get("quality", "1080p")
            )
            for entry in entries:
                if not entry:
                    continue
                title = entry.get("title", "Unknown")
                filepath = entry.get("requested_downloads", [{}])[0].get(
                    "filepath", ""
                ) if entry.get("requested_downloads") else ""
                if self.done_cb:
                    self.done_cb(title, url, filepath, quality)

    def download(self, url, settings):
        """Blocking download. Run this on a worker thread.

        Tries without cookies first. If the content is gated and cookies are
        configured, retries once with them - so public videos never send your
        login data.
        """
        self._cancel = False
        has_cookies = bool(cookie_opts(settings))
        try:
            try:
                self._run(url, settings, use_cookies=False)
            except yt_dlp.utils.DownloadCancelled:
                raise
            except Exception as e:  # noqa: BLE001
                if has_cookies and needs_auth(str(e)):
                    self._run(url, settings, use_cookies=True)
                else:
                    raise
        except yt_dlp.utils.DownloadCancelled:
            if self.error_cb:
                self.error_cb("Cancelled")
        except Exception as e:  # noqa: BLE001
            if self.error_cb:
                self.error_cb(friendly_error(str(e)))
