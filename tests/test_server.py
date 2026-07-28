"""EngineServer: HTTP surface over a QueueManager, driven with fakes."""
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from yt7th_engine.queue_manager import QueueManager
from yt7th_engine.server import EngineServer, TOKEN_HEADER


def wait_for(pred, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


class FakeDownloader:
    def __init__(self, progress_cb=None, done_cb=None, error_cb=None):
        self.progress_cb = progress_cb
        self.done_cb = done_cb
        self.error_cb = error_cb
        self.release = threading.Event()
        self.release.set()
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()
        self.release.set()

    def download(self, url, settings):
        self.release.wait(timeout=2)
        if self.cancelled.is_set():
            self.error_cb("Cancelled")
            return
        self.done_cb("Title", url, "/fake/clip.mp4", settings.get("quality", ""))


def instant_fetch(url, settings):
    return {"title": f"Video {url}", "channel": "Ch", "duration": 10,
            "thumbnail_url": "", "is_playlist": False, "entry_count": 1}


@pytest.fixture
def server(monkeypatch):
    # Never touch the real settings file or history DB.
    monkeypatch.setattr("yt7th_engine.server.data.load_settings",
                        lambda: {"quality": "1080p", "format": "MP4"})
    mgr = QueueManager(
        downloader_factory=FakeDownloader,
        info_fetcher=instant_fetch,
        space_check=lambda s: None,
        on_file_done=lambda *a: None,
    )
    srv = EngineServer(port=0, manager=mgr).start_background()
    yield srv
    srv.shutdown()


def req(srv, method, path, body=None, token="__use__"):
    headers = {"Content-Type": "application/json"}
    if token == "__use__":
        headers[TOKEN_HEADER] = srv.token
    elif token is not None:
        headers[TOKEN_HEADER] = token
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(srv.base_url + path, data=data,
                               headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=3) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_health_needs_no_token(server):
    status, body = req(server, "GET", "/health", token=None)
    assert status == 200
    assert body["ok"] is True
    assert "version" in body


def test_jobs_require_token(server):
    status, body = req(server, "GET", "/jobs", token=None)
    assert status == 401


def test_submit_then_poll_to_done_with_filepath(server):
    status, job = req(server, "POST", "/jobs", {"url": "url1"})
    assert status == 201
    jid = job["id"]

    def done():
        _, j = req(server, "GET", f"/jobs/{jid}")
        return j["status"] == "done"

    assert wait_for(done, timeout=3)
    _, j = req(server, "GET", f"/jobs/{jid}")
    assert j["filepath"] == "/fake/clip.mp4"
    assert j["percent"] == 100
    assert j["title"] == "Video url1"


def test_submit_requires_url(server):
    status, body = req(server, "POST", "/jobs", {"url": "  "})
    assert status == 400


def test_list_jobs(server):
    req(server, "POST", "/jobs", {"url": "a"})
    req(server, "POST", "/jobs", {"url": "b"})
    status, body = req(server, "GET", "/jobs")
    assert status == 200
    assert {j["url"] for j in body["jobs"]} >= {"a", "b"}


def test_get_unknown_job_404(server):
    status, _ = req(server, "GET", "/jobs/9999")
    assert status == 404


def test_cancel_job(server):
    _, job = req(server, "POST", "/jobs", {"url": "url1"})
    status, body = req(server, "DELETE", f"/jobs/{job['id']}")
    assert status == 200
    assert body["ok"] is True
