"""QueueManager: sequential FIFO downloads with per-item lifecycle."""
import threading
import time

from yt7th_engine.queue_manager import QueueManager


def wait_for(pred, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


class FakeDownloader:
    """Mimics downloader.Downloader's callback contract."""

    def __init__(self, progress_cb=None, done_cb=None, error_cb=None,
                 blocked=False, fail_msg=None):
        self.progress_cb = progress_cb
        self.done_cb = done_cb
        self.error_cb = error_cb
        self.fail_msg = fail_msg
        self.cancelled = threading.Event()
        self.release = threading.Event()
        if not blocked:
            self.release.set()
        self.calls = []

    def cancel(self):
        self.cancelled.set()
        self.release.set()

    def download(self, url, settings):
        self.calls.append((url, dict(settings)))
        self.release.wait(timeout=2)
        if self.cancelled.is_set():
            self.error_cb("Cancelled")
            return
        if self.fail_msg:
            self.error_cb(self.fail_msg)
            return
        self.done_cb("Title", url, "/fake/file.mp4", settings.get("quality", ""))


def make_factory(**dl_kwargs):
    created = []

    def factory(progress_cb=None, done_cb=None, error_cb=None):
        d = FakeDownloader(progress_cb=progress_cb, done_cb=done_cb,
                           error_cb=error_cb, **dl_kwargs)
        created.append(d)
        return d

    return factory, created


def instant_fetch(url, settings):
    return {"title": f"Video {url}", "channel": "Ch", "duration": 60,
            "thumbnail_url": "", "is_playlist": False, "entry_count": 1}


def make_manager(**kw):
    kw.setdefault("info_fetcher", instant_fetch)
    kw.setdefault("space_check", lambda settings: None)
    if "downloader_factory" not in kw:
        kw["downloader_factory"], _ = make_factory()
    return QueueManager(**kw)


def item_status(mgr, item_id):
    return next(i.status for i in mgr.items() if i.id == item_id)


def test_add_fetches_metadata_then_downloads_to_done():
    factory, created = make_factory()
    mgr = make_manager(downloader_factory=factory)
    item = mgr.add("url1", {"quality": "1080p"})
    assert wait_for(lambda: item_status(mgr, item.id) == "done")
    assert item.metadata["title"] == "Video url1"
    assert created[0].calls[0][0] == "url1"


def test_items_download_in_fifo_order():
    factory, created = make_factory()
    mgr = make_manager(downloader_factory=factory)
    mgr.add("url1", {})
    mgr.add("url2", {})
    assert wait_for(lambda: len(created) == 2 and created[1].calls)
    order = [c.calls[0][0] for c in created]
    assert order == ["url1", "url2"]


def test_fetch_error_marks_item_error_and_never_downloads():
    def bad_fetch(url, settings):
        raise RuntimeError("This video is private.")

    factory, created = make_factory()
    mgr = make_manager(downloader_factory=factory, info_fetcher=bad_fetch)
    item = mgr.add("url1", {})
    assert wait_for(lambda: item_status(mgr, item.id) == "error")
    assert "private" in item.error
    assert not created


def test_download_error_continues_to_next_item():
    calls = []

    def factory(progress_cb=None, done_cb=None, error_cb=None):
        d = FakeDownloader(progress_cb=progress_cb, done_cb=done_cb,
                           error_cb=error_cb,
                           fail_msg="boom" if not calls else None)
        calls.append(d)
        return d

    mgr = make_manager(downloader_factory=factory)
    first = mgr.add("url1", {})
    second = mgr.add("url2", {})
    assert wait_for(lambda: item_status(mgr, second.id) == "done")
    assert item_status(mgr, first.id) == "error"
    assert first.error == "boom"


def test_remove_pending_item_never_downloads():
    factory, created = make_factory(blocked=True)
    mgr = make_manager(downloader_factory=factory)
    first = mgr.add("url1", {})
    second = mgr.add("url2", {})
    assert wait_for(lambda: created and created[0].calls)  # url1 downloading
    mgr.remove(second.id)
    assert item_status(mgr, second.id) == "cancelled"
    created[0].release.set()
    assert wait_for(lambda: item_status(mgr, first.id) == "done")
    assert len(created) == 1  # url2 never got a downloader


def test_remove_active_item_cancels_downloader():
    factory, created = make_factory(blocked=True)
    mgr = make_manager(downloader_factory=factory)
    item = mgr.add("url1", {})
    assert wait_for(lambda: created and created[0].calls)
    mgr.remove(item.id)
    assert wait_for(lambda: item_status(mgr, item.id) == "cancelled")
    assert created[0].cancelled.is_set()


def test_settings_snapshot_isolated_from_later_mutation():
    factory, created = make_factory(blocked=True)
    mgr = make_manager(downloader_factory=factory)
    settings = {"quality": "1080p"}
    mgr.add("url1", settings)
    settings["quality"] = "360p"
    assert wait_for(lambda: created and created[0].calls)
    created[0].release.set()
    assert created[0].calls[0][1]["quality"] == "1080p"


def test_space_check_failure_errors_item_and_continues():
    factory, created = make_factory()
    checks = iter(["Low disk space.", None])
    mgr = make_manager(downloader_factory=factory,
                       space_check=lambda settings: next(checks))
    first = mgr.add("url1", {})
    second = mgr.add("url2", {})
    assert wait_for(lambda: item_status(mgr, second.id) == "done")
    assert item_status(mgr, first.id) == "error"
    assert "disk space" in first.error.lower()
    assert len(created) == 1


def test_on_file_done_passthrough():
    done = []
    mgr = make_manager(on_file_done=lambda *a: done.append(a))
    mgr.add("url1", {"quality": "720p"})
    assert wait_for(lambda: done)
    assert done[0] == ("Title", "url1", "/fake/file.mp4", "720p")


def test_on_update_reports_status_transitions():
    seen = []
    mgr = make_manager(on_update=lambda item: seen.append(item.status))
    item = mgr.add("url1", {})
    assert wait_for(lambda: item_status(mgr, item.id) == "done")
    assert seen[0] == "fetching"
    assert "queued" in seen
    assert seen[-1] == "done"
