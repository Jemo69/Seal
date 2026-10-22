"""The history of the downloaded files."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import data_dir


@dataclass
class HistoryEntry:
    """A file that was downloaded by this application."""

    title: str
    url: str
    path: str
    uploader: str = ""
    duration: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def exists(self) -> bool:
        return bool(self.path) and Path(self.path).exists()


class History:
    """Stores the downloaded files in a json file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (data_dir() / "history.json")
        self._lock = threading.Lock()
        self._entries: list[HistoryEntry] = self._load()

    @property
    def entries(self) -> list[HistoryEntry]:
        with self._lock:
            return list(self._entries)

    def add(self, entry: HistoryEntry) -> None:
        with self._lock:
            self._entries.insert(0, entry)
            self._entries = self._entries[:500]
            self._save()

    def remove(self, entry: HistoryEntry) -> None:
        with self._lock:
            self._entries = [item for item in self._entries if item.path != entry.path]
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._entries = []
            self._save()

    def _load(self) -> list[HistoryEntry]:
        if not self._path.exists():
            return []
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        entries = []
        for item in payload:
            try:
                entries.append(HistoryEntry(**item))
            except TypeError:
                continue
        return entries

    def _save(self) -> None:
        payload = [asdict(entry) for entry in self._entries]
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass
