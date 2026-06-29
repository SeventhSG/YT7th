import sys
import subprocess
import auth


def test_browser_running_macos_true(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(auth.os, "name", "posix")

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="12345\n", stderr="")

    monkeypatch.setattr(auth.subprocess, "run", fake_run)
    assert auth.browser_running("chrome") is True


def test_browser_running_macos_false(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(auth.os, "name", "posix")

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.setattr(auth.subprocess, "run", fake_run)
    assert auth.browser_running("chrome") is False


def test_browser_running_unknown_browser(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert auth.browser_running("none") is False
