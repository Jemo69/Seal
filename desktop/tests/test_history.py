"""Tests of the history and of the small helpers of the user interface."""

from __future__ import annotations

from pathlib import Path

from seal.history import History, HistoryEntry
from seal.ui.download_tab import extract_urls


def test_history_add_and_remove(tmp_path: Path) -> None:
    history = History(tmp_path / "history.json")
    entry = HistoryEntry(title="A video", url="https://example.com", path=str(tmp_path / "a.mp4"))
    history.add(entry)
    assert len(history.entries) == 1

    # the history is written to disk and read again
    reloaded = History(tmp_path / "history.json")
    assert reloaded.entries[0].title == "A video"

    history.remove(entry)
    assert history.entries == []


def test_history_ignores_broken_files(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text("{not json")
    assert History(path).entries == []


def test_history_ignores_a_file_that_is_not_a_list(tmp_path: Path) -> None:
    """A file that holds something else must not stop the application."""
    path = tmp_path / "history.json"
    path.write_text("5")
    assert History(path).entries == []


def test_extract_urls() -> None:
    text = "look at this https://example.com/video and https://example.com/other too"
    assert extract_urls(text) == ["https://example.com/video", "https://example.com/other"]
    assert extract_urls("nothing here") == []
