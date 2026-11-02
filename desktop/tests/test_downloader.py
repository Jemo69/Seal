"""Tests of the yt-dlp integration."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from seal import downloader
from seal.config import Settings
from seal.downloader import (
    DownloadManager,
    _parse_extra_args,
    _parse_rate,
    format_duration,
    format_size,
)
from seal.models import Task, TaskState


class FakeYtdlp:
    """A stand in for yt-dlp that does not touch the network."""

    def __init__(self, options: dict) -> None:
        self.options = options

    def __enter__(self) -> "FakeYtdlp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def extract_info(self, url: str, download: bool = False) -> dict | None:
        return {"_filename": f"{url}.mp4"}


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


def test_a_failed_download_is_not_shown_as_finished(monkeypatch, tmp_path: Path) -> None:
    """yt-dlp hides the error of an extraction, the download has to fail anyway."""

    class FailingYtdlp(FakeYtdlp):
        def extract_info(self, url: str, download: bool = False) -> dict | None:
            self.options["logger"].error("ERROR: [youtube] abc: This video is private")
            return None

    monkeypatch.setattr(downloader, "yt_dlp", SimpleNamespace(YoutubeDL=FailingYtdlp))
    manager = DownloadManager(Settings(download_dir=str(tmp_path)))
    task = Task(url="https://example.com/video")

    manager._run_download(task)

    assert task.state is TaskState.ERROR
    assert "private" in task.error.lower()
    assert not task.filename


def test_a_removed_download_does_not_continue() -> None:
    """The flag of a cancel must not be cleared, the download would go on."""
    manager = DownloadManager(Settings())
    task = Task(url="https://example.com/video")
    manager._tasks[task.task_id] = task

    manager.cancel(task.task_id)
    manager.remove(task.task_id)

    assert manager._is_stopped(task.task_id)


def test_only_a_few_downloads_run_at_the_same_time(monkeypatch, tmp_path: Path) -> None:
    """The settings say how many downloads may run at the same time."""
    running = 0
    peak = 0
    guard = threading.Lock()

    class SlowYtdlp(FakeYtdlp):
        def extract_info(self, url: str, download: bool = False) -> dict | None:
            nonlocal running, peak
            with guard:
                running += 1
                peak = max(peak, running)
            time.sleep(0.05)
            with guard:
                running -= 1
            return {"_filename": f"{url}.mp4"}

    monkeypatch.setattr(downloader, "yt_dlp", SimpleNamespace(YoutubeDL=SlowYtdlp))
    manager = DownloadManager(
        Settings(download_dir=str(tmp_path), max_concurrent_downloads=2)
    )
    tasks = [Task(url=f"https://example.com/{index}") for index in range(5)]
    for task in tasks:
        manager.enqueue(task)

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not all(t.state.is_finished for t in tasks):
        time.sleep(0.02)

    assert all(task.state is TaskState.COMPLETED for task in tasks)
    assert 1 < peak <= 2


def test_only_the_first_video_of_a_playlist_is_downloaded(tmp_path: Path) -> None:
    manager = DownloadManager(Settings(download_dir=str(tmp_path)))
    task = Task(url="https://example.com/list", is_playlist=True, playlist=False)
    assert manager._download_options(task)["playlist_items"] == "1"

    task = Task(url="https://example.com/list", is_playlist=True, playlist=True)
    assert "playlist_items" not in manager._download_options(task)

    task = Task(url="https://example.com/video", is_playlist=False)
    assert "playlist_items" not in manager._download_options(task)
