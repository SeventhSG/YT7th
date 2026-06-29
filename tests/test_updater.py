import json
import io
import updater


def test_is_newer():
    assert updater.is_newer("0.7.0", "0.6.0") is True
    assert updater.is_newer("v0.6.1", "0.6.0") is True
    assert updater.is_newer("0.6.0", "0.6.0") is False
    assert updater.is_newer("0.5.0", "0.6.0") is False


def test_check_for_update_returns_newer(monkeypatch):
    payload = json.dumps({
        "tag_name": "v0.7.0",
        "html_url": "https://github.com/SeventhSG/YT7th/releases/tag/v0.7.0",
    }).encode()

    class FakeResp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(updater, "__version__", "0.6.0")
    monkeypatch.setattr(updater.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResp(payload))
    result = updater.check_for_update()
    assert result == {
        "version": "0.7.0",
        "url": "https://github.com/SeventhSG/YT7th/releases/tag/v0.7.0",
    }


def test_check_for_update_none_when_current(monkeypatch):
    payload = json.dumps({"tag_name": "v0.6.0", "html_url": "x"}).encode()

    class FakeResp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(updater, "__version__", "0.6.0")
    monkeypatch.setattr(updater.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResp(payload))
    assert updater.check_for_update() is None


def test_check_for_update_swallows_errors(monkeypatch):
    def boom(req, timeout=0):
        raise OSError("network down")

    monkeypatch.setattr(updater.urllib.request, "urlopen", boom)
    assert updater.check_for_update() is None
