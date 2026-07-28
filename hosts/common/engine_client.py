"""Stdlib-only client for the YT7th engine daemon.

Host plugins (DaVinci Resolve, Premiere, ...) run inside an interpreter that
does NOT have the engine's dependencies (yt-dlp, a JS runtime, ...). So this
module never imports `yt7th_engine`; it only speaks HTTP to the daemon and,
when needed, launches the bundled engine binary as a separate process.

Typical use:
    client = connect()                 # find or launch the engine
    job = client.submit(url, settings) # -> {"id": ...}
    job = client.get_job(job["id"])    # poll until status in DONE/ERROR
"""
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TOKEN_HEADER = "X-YT7th-Token"
TERMINAL = ("done", "error", "cancelled")


def app_data_dir():
    """Mirror of yt7th_engine.data.app_data_dir (kept dependency-free here)."""
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "YT7th"


STATE_PATH = app_data_dir() / "engine.json"


class EngineError(RuntimeError):
    """Raised when the engine can't be reached, launched, or returns an error."""


class EngineClient:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _call(self, method, path, body=None, timeout=15):
        data = json.dumps(body).encode() if body is not None else None
        headers = {TOKEN_HEADER: self.token}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base_url + path, data=data,
                                     headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode()).get("error", str(e))
            except Exception:  # noqa: BLE001
                msg = str(e)
            raise EngineError(msg)
        except (urllib.error.URLError, OSError) as e:
            raise EngineError(f"Could not reach the engine: {e}")

    def submit(self, url, settings=None):
        return self._call("POST", "/jobs", {"url": url, "settings": settings or {}})

    def get_job(self, job_id):
        return self._call("GET", f"/jobs/{job_id}")

    def list_jobs(self):
        return self._call("GET", "/jobs").get("jobs", [])

    def cancel(self, job_id):
        return self._call("DELETE", f"/jobs/{job_id}")


# --- locating / launching the daemon -------------------------------------

def _read_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _health(base_url, timeout=1.5):
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _base_url(state):
    return f"http://127.0.0.1:{state['port']}"


def _launch_command():
    """How to start the engine, in priority order:

    1. YT7TH_ENGINE_CMD env var (a full command line) - dev/advanced.
    2. A bundled engine binary sitting next to this plugin (YT7th[.exe]).

    Returns an argv list, or None if no launcher is known.
    """
    override = os.getenv("YT7TH_ENGINE_CMD")
    if override:
        return shlex.split(override, posix=(os.name != "nt"))

    if os.name == "nt":
        names = ["YT7th.exe"]
    elif sys.platform == "darwin":
        names = ["YT7th.app/Contents/MacOS/YT7th", "YT7th"]
    else:
        names = ["YT7th"]
    here = Path(__file__).resolve()
    for base in (here.parent, here.parent.parent, here.parent.parent.parent):
        for name in names:
            candidate = base / "engine" / name
            if candidate.exists():
                return [str(candidate), "--serve"]
    return None


def _spawn(argv):
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
              "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, **kwargs)


def connect(timeout=20.0):
    """Return an EngineClient for a live engine, launching one if needed."""
    state = _read_state()
    if state and _health(_base_url(state)):
        return EngineClient(_base_url(state), state["token"])

    argv = _launch_command()
    if not argv:
        raise EngineError(
            "YT7th engine is not running and no launcher was found. "
            "Start the YT7th app, or set YT7TH_ENGINE_CMD to the engine command."
        )
    _spawn(argv)
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = _read_state()
        if state and _health(_base_url(state)):
            return EngineClient(_base_url(state), state["token"])
        time.sleep(0.25)
    raise EngineError("YT7th engine did not start in time.")
