"""Tests of the settings."""

from __future__ import annotations

import json
from pathlib import Path

from seal import config
from seal.config import Settings


def test_defaults_are_filled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    settings = Settings()
    assert settings.download_dir
    assert settings.audio_dir.endswith("Audio")
    assert settings.max_concurrent_downloads >= 1


def test_save_and_load(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    settings = Settings()
    settings.download_dir = str(tmp_path / "downloads")
    settings.audio_format = "mp3"
    settings.embed_thumbnail = False
    settings.max_concurrent_downloads = 5
    settings.save()

    loaded = Settings.load()
    assert loaded.download_dir == str(tmp_path / "downloads")
    assert loaded.audio_format == "mp3"
    assert loaded.embed_thumbnail is False
    assert loaded.max_concurrent_downloads == 5


def test_load_ignores_unknown_values(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text(json.dumps({"theme": "dark", "nonsense": 1}))
    settings = Settings.load()
    assert settings.theme == "dark"


def test_load_ignores_broken_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text("{not json")
    assert Settings.load().theme == "system"


def test_target_dir(tmp_path: Path) -> None:
    settings = Settings(download_dir=str(tmp_path / "videos"), audio_dir=str(tmp_path / "audio"))
    assert settings.target_dir(audio=False).name == "videos"
    assert settings.target_dir(audio=True).name == "audio"
    assert settings.target_dir().is_dir()
