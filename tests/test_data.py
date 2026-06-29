import sys
import importlib
from pathlib import Path


def _reload_data(monkeypatch, platform, home, appdata=None):
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("HOME", str(home))
    if appdata is not None:
        monkeypatch.setenv("APPDATA", str(appdata))
    else:
        monkeypatch.delenv("APPDATA", raising=False)
    import data
    return importlib.reload(data)


def test_macos_uses_application_support(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    d = _reload_data(monkeypatch, "darwin", tmp_path)
    assert d.app_data_dir() == tmp_path / "Library" / "Application Support" / "YT7th"


def test_windows_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    appdata = tmp_path / "AppData" / "Roaming"
    d = _reload_data(monkeypatch, "win32", tmp_path, appdata=appdata)
    assert d.app_data_dir() == appdata / "YT7th"


def test_linux_uses_local_share(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    d = _reload_data(monkeypatch, "linux", tmp_path)
    assert d.app_data_dir() == tmp_path / ".local" / "share" / "YT7th"
