"""Tests of the messages of the downloader."""

from __future__ import annotations

from pathlib import Path

from seal.config import Settings
from seal.downloader import DownloadManager, friendly_error


def test_the_login_hint_is_shown() -> None:
    message = friendly_error(
        "ERROR: [youtube] Sc5ca: Sign in to confirm you're not a bot. Use --cookies-from-browser"
    )
    assert "login" in message.lower()
    assert "cookies" in message.lower()


def test_a_private_video_is_explained() -> None:
    assert "private" in friendly_error("ERROR: [youtube] This video is private").lower()


def test_an_unsupported_link_is_explained() -> None:
    assert "does not offer" in friendly_error("ERROR: Unsupported URL").lower()


def test_other_errors_are_kept() -> None:
    assert friendly_error("something went wrong") == "something went wrong"


def test_the_cookies_of_the_browser_are_used(tmp_path: Path) -> None:
    manager = DownloadManager(Settings(download_dir=str(tmp_path), cookies_from_browser="chrome"))
    options = manager._info_options()
    assert options["cookiesfrombrowser"] == ("chrome", None, None, None)


def test_a_cookies_file_is_used(tmp_path: Path) -> None:
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n")
    manager = DownloadManager(Settings(download_dir=str(tmp_path), cookies_file=str(cookies)))
    assert manager._info_options()["cookiefile"] == str(cookies)


def test_the_errors_of_the_extraction_are_not_swallowed(tmp_path: Path) -> None:
    """yt-dlp hides the error of an extraction when ignoreerrors is set."""
    manager = DownloadManager(Settings(download_dir=str(tmp_path)))
    assert manager._info_options()["ignoreerrors"] is False
    # a download may fail without stopping the whole playlist
    assert manager._download_options.__self__ is manager
