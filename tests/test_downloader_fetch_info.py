"""fetch_info: metadata without downloading, with the same auth retry."""
import pytest

from yt7th_engine import downloader


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL as a context manager."""

    def __init__(self, info=None, error=None):
        self.info = info
        self.error = error
        self.opts_seen = []

    def __call__(self, opts):
        self.opts_seen.append(opts)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download):
        assert download is False
        if self.error:
            raise self.error
        return self.info


VIDEO_INFO = {
    "title": "A Video",
    "channel": "A Channel",
    "duration": 123,
    "thumbnail": "https://i.ytimg.com/vi/x/hq720.jpg",
}

PLAYLIST_INFO = {
    "title": "A Playlist",
    "uploader": "Someone",
    "entries": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
    "thumbnails": [{"url": "https://i.ytimg.com/pl.jpg"}],
}


def test_video_field_mapping(monkeypatch):
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL(info=VIDEO_INFO))
    meta = downloader.fetch_info("url", {})
    assert meta == {
        "title": "A Video",
        "channel": "A Channel",
        "duration": 123,
        "thumbnail_url": "https://i.ytimg.com/vi/x/hq720.jpg",
        "is_playlist": False,
        "entry_count": 1,
    }


def test_playlist_detection_and_count(monkeypatch):
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL",
                        FakeYDL(info=PLAYLIST_INFO))
    meta = downloader.fetch_info("url", {})
    assert meta["is_playlist"] is True
    assert meta["entry_count"] == 3
    assert meta["channel"] == "Someone"
    assert meta["thumbnail_url"] == "https://i.ytimg.com/pl.jpg"


def test_error_propagates(monkeypatch):
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL",
                        FakeYDL(error=RuntimeError("Video unavailable")))
    with pytest.raises(RuntimeError):
        downloader.fetch_info("url", {})


def test_gated_content_retries_with_cookies(monkeypatch):
    """First try carries no cookies; auth errors retry once with them."""
    fake = FakeYDL(info=VIDEO_INFO)
    calls = []

    def extract(url, download):
        calls.append(len(fake.opts_seen))
        if len(fake.opts_seen) == 1:
            raise RuntimeError("This is a private video")
        return VIDEO_INFO

    fake.extract_info = extract
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", fake)
    monkeypatch.setattr(downloader, "cookie_opts",
                        lambda s: {"cookiefile": "c.txt"})

    meta = downloader.fetch_info("url", {"cookies_file": "c.txt"})
    assert meta["title"] == "A Video"
    assert "cookiefile" not in fake.opts_seen[0]
    assert fake.opts_seen[1]["cookiefile"] == "c.txt"


def test_no_cookie_retry_without_cookies(monkeypatch):
    fake = FakeYDL(error=RuntimeError("This is a private video"))
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", fake)
    monkeypatch.setattr(downloader, "cookie_opts", lambda s: {})
    with pytest.raises(RuntimeError):
        downloader.fetch_info("url", {})
    assert len(fake.opts_seen) == 1
