"""EngineClient <-> EngineServer integration, plus locate/launch logic."""
import threading
import time

import pytest

from hosts.common import engine_client as ec
from yt7th_engine.queue_manager import QueueManager
from yt7th_engine.server import EngineServer


def wait_for(pred, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


class FakeDownloader:
    def __init__(self, progress_cb=None, done_cb=None, error_cb=None):
        self.done_cb = done_cb
        self.error_cb = error_cb

    def cancel(self):
        pass

    def download(self, url, settings):
        self.done_cb("Title", url, "/fake/clip.mp4", settings.get("quality", ""))


def instant_fetch(url, settings):
    return {"title": f"Video {url}", "channel": "Ch", "is_playlist": False,
            "entry_count": 1, "duration": 1, "thumbnail_url": ""}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("yt7th_engine.server.data.load_settings",
                        lambda: {"quality": "1080p"})
    mgr = QueueManager(downloader_factory=FakeDownloader,
                       info_fetcher=instant_fetch,
                       space_check=lambda s: None,
                       on_file_done=lambda *a: None)
    srv = EngineServer(port=0, manager=mgr).start_background()
    yield ec.EngineClient(srv.base_url, srv.token)
    srv.shutdown()


def test_submit_and_poll(client):
    job = client.submit("url1", {"quality": "720p"})
    jid = job["id"]
    assert wait_for(lambda: client.get_job(jid)["status"] == "done")
    assert client.get_job(jid)["filepath"] == "/fake/clip.mp4"


def test_list_jobs(client):
    client.submit("a")
    client.submit("b")
    assert wait_for(lambda: len(client.list_jobs()) >= 2)


def test_bad_token_raises_engine_error(client):
    bad = ec.EngineClient(client.base_url, "wrong")
    with pytest.raises(ec.EngineError):
        bad.list_jobs()


def test_unreachable_engine_raises(monkeypatch):
    bad = ec.EngineClient("http://127.0.0.1:1", "tok")
    with pytest.raises(ec.EngineError):
        bad.list_jobs()


def test_connect_reuses_running_engine(monkeypatch, client):
    # Point the locator's state at our live test server.
    port = int(client.base_url.rsplit(":", 1)[1])
    monkeypatch.setattr(ec, "_read_state",
                        lambda: {"port": port, "token": client.token, "pid": 1})
    monkeypatch.setattr(ec, "_spawn",
                        lambda argv: pytest.fail("should not spawn"))
    got = ec.connect()
    assert got.base_url == client.base_url
    assert got.token == client.token


def test_connect_errors_without_launcher(monkeypatch):
    monkeypatch.setattr(ec, "_read_state", lambda: None)
    monkeypatch.setattr(ec, "_launch_command", lambda: None)
    with pytest.raises(ec.EngineError):
        ec.connect(timeout=0.1)
