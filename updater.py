"""Check GitHub Releases for a newer YT7th, off the UI thread."""
import json
import threading
import urllib.error
import urllib.request

from version import __version__

REPO = "SeventhSG/YT7th"
_API = f"https://api.github.com/repos/{REPO}/releases/latest"


def _parse(tag):
    return tuple(int(x) for x in tag.lstrip("v").split(".") if x.isdigit())


def is_newer(latest, current):
    try:
        return _parse(latest) > _parse(current)
    except (ValueError, AttributeError):
        return False


def check_for_update(timeout=4):
    """Return {"version", "url"} if a newer release exists, else None.
    Silent on any network/parse error."""
    try:
        req = urllib.request.Request(_API, headers={
            "User-Agent": f"YT7th/{__version__}",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        tag = data.get("tag_name", "")
        if tag and is_newer(tag, __version__):
            return {"version": tag.lstrip("v"), "url": data.get("html_url", "")}
        return None
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return None


def check_async(callback):
    """Run check_for_update on a daemon thread; call callback(result)."""
    def worker():
        callback(check_for_update())
    threading.Thread(target=worker, daemon=True).start()
