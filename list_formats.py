"""Diagnostic: list the formats yt-dlp sees for a URL, using your saved
settings and cookies. Run: python list_formats.py <url>
"""
import sys

import yt_dlp

import data
from auth import cookie_opts


def main():
    if len(sys.argv) < 2:
        print("Usage: python list_formats.py <url>")
        return
    url = sys.argv[1]
    settings = data.load_settings()
    # Show warnings (SABR / po_token notices) and just list formats,
    # which avoids triggering format selection.
    opts = {"listformats": True, "verbose": True}
    opts.update(cookie_opts(settings))

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=False)


if __name__ == "__main__":
    main()
