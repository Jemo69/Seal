"""Tests of the yt-dlp integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from seal.config import Settings
from seal.downloader import (
    DownloadManager,
    _parse_extra_args,
    _parse_rate,
    format_duration,
    format_size,
)
from seal.models import Task


def test_format_size() -> None:
    assert format_size(None) == ""
    assert format_size(512) == "512 B"
    assert format_size(1024) == "1.0 KiB"
    assert format_size(1024 * 1024 * 3) == "3.0 MiB"


def test_format_duration() -> None:
    assert format_duration(None) == ""
    assert format_duration(65) == "1:05"
    assert format_duration(3725) == "1:02:05"


def test_parse_rate() -> None:
    assert _parse_rate("") == 0
    assert _parse_rate("1M") == 1024 * 1024
    assert _parse_rate("500K") == 500 * 1024
    assert _parse_rate("nonsense") == 0


def test_parse_extra_args() -> None:
    options = _parse_extra_args("--retries 5 --no-part")
    assert options["retries"] == "5"
    assert options["no_part"] is True


def test_download_options_use_the_settings(tmp_path: Path) -> None:
    settings = Settings(
        download_dir=str(tmp_path),
        audio_dir=str(tmp_path / "Audio"),
        audio_format="mp3",
        proxy="http://localhost:8080",
        rate_limit="1M",
    )
    manager = DownloadManager(settings)
    task = Task(url="https://example.com", audio_only=True, format_id="140")
    options = manager._download_options(task)

    assert options["format"] == "140"
    assert options["proxy"] == "http://localhost:8080"
    assert options["ratelimit"] == 1024 * 1024
    assert options["paths"]["home"].endswith("Audio")
    postprocessors = [entry["key"] for entry in options["postprocessors"]]
    assert "FFmpegExtractAudio" in postprocessors


def test_info_options_skip_the_download(tmp_path: Path) -> None:
    manager = DownloadManager(Settings(download_dir=str(tmp_path)))
    options = manager._info_options()
    assert options["skip_download"] is True


@pytest.mark.skipif(not pytest.importorskip("yt_dlp"), reason="yt-dlp is not installed")
def test_fetch_info_reports_errors(tmp_path: Path) -> None:
    """A link that cannot be read is reported to the user."""
    manager = DownloadManager(Settings(download_dir=str(tmp_path)))
    results: list[tuple] = []

    def on_done(info, error):  # noqa: ANN001 - the callback of the manager
        results.append((info, error))

    manager.fetch_info("this is not a link", on_done).join(timeout=60)
    assert results, "the download manager did not report anything"
    info, error = results[0]
    assert info is None
    assert error
