"""import_finished_job orchestration against a fake Resolve."""
import pytest

from hosts.common.importer import import_finished_job
from hosts.resolve.resolve_host import FakeResolveHost


def test_imports_to_media_pool_only():
    host = FakeResolveHost(has_timeline=True)
    job = {"files": ["/a.mp4"], "filepath": "/a.mp4"}
    res = import_finished_job(host, job, append_to_timeline=False)
    assert host.imported == ["/a.mp4"]
    assert host.appended == []
    assert res.imported == ["/a.mp4"]


def test_appends_when_requested_and_timeline_open():
    host = FakeResolveHost(has_timeline=True, import_returns=["CLIP"])
    job = {"files": ["/a.mp4"]}
    res = import_finished_job(host, job, append_to_timeline=True)
    assert host.imported == ["/a.mp4"]
    assert host.appended == ["CLIP"]
    assert res.appended == ["CLIP"]


def test_append_requested_but_no_timeline_falls_back_to_pool():
    host = FakeResolveHost(has_timeline=False)
    job = {"files": ["/a.mp4"]}
    res = import_finished_job(host, job, append_to_timeline=True)
    assert host.imported == ["/a.mp4"]
    assert host.appended == []
    assert "timeline" in res.message.lower()


def test_multiple_files_playlist():
    host = FakeResolveHost(has_timeline=True, import_returns=["c1", "c2"])
    job = {"files": ["/a.mp4", "/b.mp4"]}
    res = import_finished_job(host, job, append_to_timeline=True)
    assert host.imported == ["/a.mp4", "/b.mp4"]
    assert host.appended == ["c1", "c2"]


def test_uses_filepath_when_files_absent():
    host = FakeResolveHost()
    job = {"filepath": "/only.mp4"}
    res = import_finished_job(host, job)
    assert res.imported == ["/only.mp4"]


def test_no_files_raises():
    host = FakeResolveHost()
    with pytest.raises(ValueError):
        import_finished_job(host, {"files": [], "filepath": ""})
