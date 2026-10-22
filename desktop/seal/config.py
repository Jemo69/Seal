"""Persistent settings of the application.

The settings are stored as json below the application data directory of the current user, the
same location the Android application uses for its own preferences.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

APP_NAME = "Seal"


def data_dir() -> Path:
    """The directory the application stores its data in."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_download_dir() -> Path:
    """The directory the downloads are written to by default."""
    downloads = Path.home() / "Downloads"
    if not downloads.is_dir():
        downloads = data_dir() / "Downloads"
    return downloads / APP_NAME


@dataclass
class Settings:
    """Every setting the application knows about."""

    # Where the files are written to.
    download_dir: str = ""
    audio_dir: str = ""

    # The format of the downloaded files.
    video_quality: str = "best"
    audio_format: str = "m4a"
    audio_only: bool = False
    merge_output_format: str = "mkv"

    # What yt-dlp should embed.
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    write_subtitles: bool = False
    embed_subtitles: bool = False
    subtitle_langs: str = "en.*,.*-orig"
    write_auto_subs: bool = False

    # Playlists.
    download_playlist: bool = False
    playlist_items: str = ""

    # The name of the downloaded files.
    filename_template: str = "%(title).200B.%(ext)s"

    # Network.
    proxy: str = ""
    rate_limit: str = ""
    cookies_file: str = ""
    concurrent_fragments: int = 4
    max_concurrent_downloads: int = 2
    socket_timeout: int = 30

    # Instagram.
    instagram_session_file: str = ""
    instagram_download_dir: str = ""
    instagram_profile_limit: int = 25

    # Look and feel.
    theme: str = "system"

    # Extra arguments that are passed to yt-dlp.
    extra_args: str = ""

    def __post_init__(self) -> None:
        if not self.download_dir:
            self.download_dir = str(default_download_dir())
        if not self.audio_dir:
            self.audio_dir = str(Path(self.download_dir) / "Audio")
        if not self.instagram_download_dir:
            self.instagram_download_dir = str(Path(self.download_dir) / "Instagram")

    # ------------------------------------------------------------------ storage

    @property
    def path(self) -> Path:
        return data_dir() / "config.json"

    def save(self) -> None:
        payload = {f.name: getattr(self, f.name) for f in fields(self)}
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @classmethod
    def load(cls) -> "Settings":
        path = data_dir() / "config.json"
        if not path.exists():
            return cls()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        values = {key: value for key, value in payload.items() if key in known}
        settings = cls(**values)
        settings.__post_init__()
        return settings

    # ------------------------------------------------------------------ helpers

    def target_dir(self, audio: bool | None = None) -> Path:
        """The directory a download is written to."""
        use_audio = self.audio_only if audio is None else audio
        path = Path(self.audio_dir if use_audio else self.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
