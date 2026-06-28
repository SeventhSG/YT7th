"""Authentication for downloading content you have access to.

Two methods, in order of reliability:

1. cookies.txt file (recommended) - export once with a browser extension
   such as "Get cookies.txt LOCALLY". Works regardless of whether the
   browser is open, and is immune to Chromium app-bound cookie encryption.
2. Browser cookies - reads cookies directly from a browser profile. On
   Windows this fails if the browser is running (it locks the cookie
   database) and can fail on Chrome/Brave v127+ due to app-bound encryption.

For personal archival use only.
"""
import os
import subprocess

SUPPORTED_BROWSERS = ["none", "chrome", "firefox", "edge", "brave"]

# Windows process image names per browser, for the "is it running" guard.
_PROC_NAMES = {
    "chrome": "chrome.exe",
    "brave": "brave.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
}


def cookie_opts(settings):
    """Return yt-dlp options for authentication, based on settings.

    A cookies.txt file takes precedence over browser cookies when set.
    """
    cookies_file = settings.get("cookies_file", "")
    if cookies_file and os.path.exists(cookies_file):
        return {"cookiefile": cookies_file}

    browser = settings.get("cookies_browser", "none")
    if browser and browser != "none" and browser in SUPPORTED_BROWSERS:
        return {"cookiesfrombrowser": (browser,)}

    return {}


def browser_running(browser):
    """True if the given browser appears to be running (Windows only)."""
    proc = _PROC_NAMES.get(browser)
    if not proc or os.name != "nt":
        return False
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {proc}", "/NH"],
            capture_output=True, text=True, startupinfo=si, timeout=5,
        )
        return proc.lower() in out.stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return False
