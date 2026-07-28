"""service: reuse a healthy engine, otherwise spawn and await one."""
from yt7th_engine import service


def _point_state_at(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "STATE_PATH", tmp_path / "engine.json")


def test_state_roundtrip(monkeypatch, tmp_path):
    _point_state_at(monkeypatch, tmp_path)
    service.write_state(51234, "tok", 999)
    assert service.read_state() == {"port": 51234, "token": "tok", "pid": 999}
    service.clear_state()
    assert service.read_state() is None


def test_ensure_running_reuses_healthy_engine(monkeypatch, tmp_path):
    _point_state_at(monkeypatch, tmp_path)
    service.write_state(51234, "tok", 999)
    monkeypatch.setattr(service, "health", lambda url, timeout=1.5: {"ok": True})

    def boom():
        raise AssertionError("should not spawn when engine is healthy")

    monkeypatch.setattr(service, "_spawn", boom)
    base, token = service.ensure_running()
    assert base == "http://127.0.0.1:51234"
    assert token == "tok"


def test_ensure_running_spawns_when_absent(monkeypatch, tmp_path):
    _point_state_at(monkeypatch, tmp_path)
    spawned = []

    def fake_spawn():
        spawned.append(True)
        service.write_state(52000, "newtok", 111)

    # Unhealthy until spawn writes state, healthy after.
    monkeypatch.setattr(service, "_spawn", fake_spawn)
    monkeypatch.setattr(service, "health",
                        lambda url, timeout=1.5: {"ok": True}
                        if service.read_state() else None)
    base, token = service.ensure_running(timeout=5)
    assert spawned == [True]
    assert base == "http://127.0.0.1:52000"
    assert token == "newtok"


def test_ensure_running_times_out(monkeypatch, tmp_path):
    _point_state_at(monkeypatch, tmp_path)
    monkeypatch.setattr(service, "_spawn", lambda: None)
    monkeypatch.setattr(service, "health", lambda url, timeout=1.5: None)
    try:
        service.ensure_running(timeout=0.6)
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
