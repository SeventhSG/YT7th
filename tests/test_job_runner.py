"""run_job orchestration: submit -> poll -> import, host-agnostic.

Two layers of coverage:
  * fast unit tests with a fake client + fake host (deterministic states)
  * a real end-to-end pipeline test: live EngineServer + real EngineClient +
    FakeResolveHost, exercising the exact flow the Resolve plugin runs
    (everything except Resolve's UIManager widgets).
"""
import threading
import time

import pytest

from hosts.common.job_runner import run_job, JobOutcome
from hosts.resolve.resolve_host import FakeResolveHost


class FakeClient:
    """Serves a scripted sequence of job dicts from get_job."""

    def __init__(self, states):
        self._states = list(states)
        self._i = 0
        self.submitted = None

    def submit(self, url, settings):
        self.submitted = (url, settings)
        return self._states[0]

    def get_job(self, job_id):
        # advance through states, holding on the last one
        if self._i < len(self._states) - 1:
            self._i += 1
        return self._states[self._i]


def _states(*statuses, **extra):
    base = {"id": 1, "percent": 0, "title": "V", "files": [], "filepath": "",
            "error": ""}
    return [{**base, "status": s, **extra} for s in statuses]


def test_success_imports_to_media_pool():
    client = FakeClient(_states("fetching", "downloading", "done",
                                files=["/a.mp4"], filepath="/a.mp4"))
    host = FakeResolveHost(has_timeline=True)
    out = run_job(client, host, "url", {}, append_to_timeline=False,
                  sleep=lambda s: None)
    assert isinstance(out, JobOutcome)
    assert out.ok and out.status == "done"
    assert host.imported == ["/a.mp4"]
    assert client.submitted == ("url", {})


def test_success_appends_when_requested():
    client = FakeClient(_states("downloading", "done",
                                files=["/a.mp4"], filepath="/a.mp4"))
    host = FakeResolveHost(has_timeline=True, import_returns=["CLIP"])
    out = run_job(client, host, "url", {}, append_to_timeline=True,
                  sleep=lambda s: None)
    assert out.ok
    assert host.appended == ["CLIP"]


def test_engine_error_status_returns_not_ok():
    client = FakeClient(_states("downloading", "error", error="boom"))
    host = FakeResolveHost()
    out = run_job(client, host, "url", {}, sleep=lambda s: None)
    assert not out.ok and out.status == "error"
    assert "boom" in out.message
    assert host.imported == []


def test_cancelled_status_returns_not_ok():
    client = FakeClient(_states("downloading", "cancelled"))
    host = FakeResolveHost()
    out = run_job(client, host, "url", {}, sleep=lambda s: None)
    assert not out.ok and out.status == "cancelled"
    assert host.imported == []


def test_status_callback_reports_progress():
    client = FakeClient(_states("queued", "downloading", "done",
                                files=["/a.mp4"], percent=42))
    host = FakeResolveHost()
    seen = []
    run_job(client, host, "url", {}, on_status=seen.append, sleep=lambda s: None)
    assert any("Downloading" in s for s in seen)
    assert any("Importing" in s for s in seen)


def test_done_but_no_files_is_reported_not_raised():
    client = FakeClient(_states("done"))  # no files
    host = FakeResolveHost()
    out = run_job(client, host, "url", {}, sleep=lambda s: None)
    assert not out.ok
    assert "no file" in out.message.lower()


# --- real end-to-end pipeline (live daemon) ------------------------------

class _FakeDownloader:
    def __init__(self, progress_cb=None, done_cb=None, error_cb=None):
        self.done_cb = done_cb

    def cancel(self):
        pass

    def download(self, url, settings):
        self.done_cb("Title", url, "/fake/clip.mp4", settings.get("quality", ""))


def _instant_fetch(url, settings):
    return {"title": f"Video {url}", "channel": "Ch", "is_playlist": False,
            "entry_count": 1, "duration": 1, "thumbnail_url": ""}


def test_end_to_end_pipeline_live_daemon(monkeypatch):
    from yt7th_engine.queue_manager import QueueManager
    from yt7th_engine.server import EngineServer
    from hosts.common.engine_client import EngineClient

    monkeypatch.setattr("yt7th_engine.server.data.load_settings",
                        lambda: {"quality": "1080p"})
    mgr = QueueManager(downloader_factory=_FakeDownloader,
                       info_fetcher=_instant_fetch,
                       space_check=lambda s: None,
                       on_file_done=lambda *a: None)
    srv = EngineServer(port=0, manager=mgr).start_background()
    try:
        client = EngineClient(srv.base_url, srv.token)
        host = FakeResolveHost(has_timeline=True, import_returns=["CLIP"])
        out = run_job(client, host, "https://youtu.be/x",
                      {"quality": "720p"}, append_to_timeline=True,
                      poll_interval=0.05)
        assert out.ok and out.status == "done"
        assert host.imported == ["/fake/clip.mp4"]
        assert host.appended == ["CLIP"]
    finally:
        srv.shutdown()
