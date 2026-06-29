import os
import downloader
import resources


def test_build_opts_sets_ffmpeg_location_when_bundled(monkeypatch, tmp_path):
    d = tmp_path / "bin"
    d.mkdir()
    monkeypatch.setattr(resources, "bin_dir", lambda: str(d))
    monkeypatch.setattr(downloader.resources, "bin_dir", lambda: str(d),
                        raising=False)
    dl = downloader.Downloader()
    opts = dl._build_opts({"download_dir": str(tmp_path / "out"),
                           "quality": "1080p", "format": "MP4"})
    assert opts["ffmpeg_location"] == str(d)


def test_build_opts_no_ffmpeg_location_without_bin(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader.resources, "bin_dir",
                        lambda: str(tmp_path / "nope"), raising=False)
    dl = downloader.Downloader()
    opts = dl._build_opts({"download_dir": str(tmp_path / "out"),
                           "quality": "1080p", "format": "MP4"})
    assert "ffmpeg_location" not in opts
