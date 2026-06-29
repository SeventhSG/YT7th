import os
import importlib


def test_resource_path_joins_under_root(monkeypatch):
    import resources
    importlib.reload(resources)
    p = resources.resource_path("assets", "logo.png")
    assert p.endswith(os.path.join("assets", "logo.png"))
    assert os.path.isabs(p)


def test_bootstrap_prepends_bin_to_path(monkeypatch, tmp_path):
    import resources
    importlib.reload(resources)
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    (bin_path / "deno").write_text("#!/bin/sh\n")
    monkeypatch.setattr(resources, "bin_dir", lambda: str(bin_path))
    monkeypatch.setenv("PATH", "/usr/bin")
    resources.bootstrap()
    assert os.environ["PATH"].split(os.pathsep)[0] == str(bin_path)


def test_bootstrap_noop_without_bin(monkeypatch, tmp_path):
    import resources
    importlib.reload(resources)
    monkeypatch.setattr(resources, "bin_dir", lambda: str(tmp_path / "nope"))
    before = os.environ.get("PATH", "")
    resources.bootstrap()
    assert os.environ.get("PATH", "") == before
