"""The data the application passes around."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class TaskState(enum.Enum):
    """The state of a download."""

    QUEUED = "queued"
    FETCHING = "fetching"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELED = "canceled"
    ERROR = "error"

    @property
    def is_finished(self) -> bool:
        return self in (TaskState.COMPLETED, TaskState.CANCELED, TaskState.ERROR)


@dataclass
class Format:
    """A single format offered by the website."""

    format_id: str
    ext: str
    resolution: str = ""
    note: str = ""
    filesize: int | None = None
    vcodec: str = "none"
    acodec: str = "none"
    fps: float | None = None
    tbr: float | None = None

    @property
    def has_video(self) -> bool:
        return self.vcodec not in ("", "none")

    @property
    def has_audio(self) -> bool:
        return self.acodec not in ("", "none")

    @property
    def height(self) -> int:
        """The height of the format, a resolution looks like 1920x1080."""
        if not self.resolution:
            return 0
        parts = self.resolution.lower().split("x")
        for part in reversed(parts):
            digits = "".join(char for char in part if char.isdigit())
            if digits:
                return int(digits)
        return 0

    @property
    def label(self) -> str:
        parts = [self.resolution or self.note or self.format_id, self.ext]
        if self.tbr:
            parts.append(f"{self.tbr:.0f} kbps")
        return " - ".join(part for part in parts if part)


@dataclass
class VideoInfo:
    """Everything the application knows about a video."""

    url: str
    title: str = ""
    uploader: str = ""
    duration: int = 0
    thumbnail: str = ""
    extractor: str = ""
    is_playlist: bool = False
    playlist_count: int = 0
    entries: list[str] = field(default_factory=list)
    formats: list[Format] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_text(self) -> str:
        seconds = int(self.duration or 0)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    @classmethod
    def from_info(cls, url: str, info: dict[str, Any]) -> "VideoInfo":
        """Builds the info from the dictionary yt-dlp returns."""
        formats = [
            Format(
                format_id=entry.get("format_id") or "",
                ext=entry.get("ext") or "",
                resolution=entry.get("resolution") or "",
                note=entry.get("format_note") or "",
                filesize=entry.get("filesize") or entry.get("filesize_approx"),
                vcodec=entry.get("vcodec") or "none",
                acodec=entry.get("acodec") or "none",
                fps=entry.get("fps"),
                tbr=entry.get("tbr"),
            )
            for entry in (info.get("formats") or [])
            if entry.get("format_id")
        ]
        entries = [
            entry.get("url") or entry.get("webpage_url") or ""
            for entry in (info.get("entries") or [])
            if entry
        ]
        return cls(
            url=url,
            title=info.get("title") or url,
            uploader=info.get("uploader") or info.get("channel") or "",
            duration=int(info.get("duration") or 0),
            thumbnail=info.get("thumbnail") or "",
            extractor=info.get("extractor_key") or "",
            is_playlist=info.get("_type") == "playlist",
            playlist_count=len(entries) or int(info.get("playlist_count") or 0),
            entries=entries,
            formats=formats,
            raw=info,
        )


@dataclass
class Task:
    """A download that is running or has been finished."""

    url: str
    title: str = ""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: TaskState = TaskState.QUEUED
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    size: str = ""
    filename: str = ""
    error: str = ""
    audio_only: bool = False
    format_id: str = ""
    playlist: bool = False

    @property
    def progress_percent(self) -> int:
        return int(max(0.0, min(1.0, self.progress)) * 100)
