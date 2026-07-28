"""Daemon lifecycle: find a running engine or auto-launch one.

State lives in `<app_data>/engine.json` as {port, token, pid}. A host client
calls `ensure_running()` to get a (base_url, token) it can drive. If the
recorded engine answers /health it is reused; otherwise a fresh detached
engine process is spawned and awaited.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from . import data

STATE_PATH = data.app_data_dir() / "engine.json"


def read_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_state(port, token, pid):
    STATE_PATH.write_text(
        json.dumps({"port": port, "token": token, "pid": pid}),
        encoding="utf-8",
    )


def clear_state():
    try:
        STATE_PATH.unlink()
    except OSError:
        pass


def health(base_url, timeout=1.5):
    """Return the parsed /health body if the engine answers, else None."""
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _base_url(state):
    return f"http://127.0.0.1:{state['port']}"


def _spawn():
    """Launch a detached engine process. Frozen build re-runs itself with
    --serve; from source we run `python -m yt7th_engine.server`."""
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--serve"]
    else:
        cmd = [sys.executable, "-m", "yt7th_engine.server"]
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
              "stdin": subprocess.DEVNULL,
              "cwd": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def ensure_running(timeout=15.0):
    """Return (base_url, token) for a live engine, launching one if needed."""
    state = read_state()
    if state and health(_base_url(state)):
        return _base_url(state), state["token"]

    _spawn()
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = read_state()
        if state and health(_base_url(state)):
            return _base_url(state), state["token"]
        time.sleep(0.25)
    raise RuntimeError("YT7th engine did not start in time.")


def run_server(port=0):
    """Blocking: start an EngineServer, publish its state, serve until killed.
    This is the entry point the spawned process runs."""
    from .server import EngineServer  # local import: avoids import at spawn cost

    server = EngineServer(port=port)
    write_state(server.port, server.token, os.getpid())
    try:
        server.serve_forever()
    finally:
        clear_state()
