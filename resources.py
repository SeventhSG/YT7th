"""Locate bundled assets/binaries in dev and inside a PyInstaller bundle,
and put bundled executables (ffmpeg, ffprobe, deno) on PATH at startup."""
import os
import stat
import sys

_BUNDLED_BINS = ("ffmpeg", "ffprobe", "deno")


def _base():
    return getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))


def resource_path(*parts):
    return os.path.join(_base(), *parts)


def bin_dir():
    return resource_path("bin")


def bootstrap():
    """Prepend the bundled bin/ dir to PATH and ensure exec bits on Unix.
    No-op when bin/ is absent (e.g. dev runs without bundled binaries)."""
    d = bin_dir()
    if not os.path.isdir(d):
        return
    os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
    if os.name != "nt":
        for name in _BUNDLED_BINS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                try:
                    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR |
                             stat.S_IXGRP | stat.S_IXOTH)
                except OSError:
                    pass
