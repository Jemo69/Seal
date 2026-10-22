"""The tab that holds the settings of the application."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import TYPE_CHECKING

from ..config import Settings
from .theme import Palette

if TYPE_CHECKING:  # pragma: no cover
    from .app import MainWindow

AUDIO_FORMATS = ("best", "m4a", "mp3", "opus", "wav", "flac")
THEMES = ("system", "light", "dark")


class SettingsTab(ttk.Frame):
    """Lets the user change every setting."""

    def __init__(self, master: tk.Misc, app: "MainWindow") -> None:
        super().__init__(master, padding=20)
        self.app = app
        self.palette: Palette = app.palette
        self.vars: dict[str, tk.Variable] = {}
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        self._build_directories()
        self._build_formats()
        self._build_network()
        self._build_instagram()
        self._build_appearance()

        buttons = ttk.Frame(self)
        buttons.grid(row=25, column=0, columnspan=2, sticky="w", pady=(24, 0))
        ttk.Button(buttons, text="Save", style="Accent.TButton", command=self.save).pack(side="left")
        ttk.Button(buttons, text="Open the data folder", command=self.open_data_dir).pack(
            side="left", padx=8
        )

        self.load()

    # ------------------------------------------------------------------ helpers

    def _entry(self, row: int, key: str, label: str, browse: str | None = None) -> None:
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=(10, 0), padx=(0, 24))
        frame = ttk.Frame(self)
        frame.grid(row=row, column=1, sticky="ew", pady=(10, 0))
        frame.columnconfigure(0, weight=1)
        var = tk.StringVar()
        self.vars[key] = var
        ttk.Entry(frame, textvariable=var).grid(row=0, column=0, sticky="ew")
        if browse:
            ttk.Button(
                frame,
                text="…",
                width=3,
                command=lambda: self._browse(var, browse),
            ).grid(row=0, column=1, padx=(6, 0))

    def _choice(self, row: int, key: str, label: str, values: tuple[str, ...]) -> None:
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=(10, 0), padx=(0, 24))
        var = tk.StringVar()
        self.vars[key] = var
        ttk.Combobox(self, textvariable=var, values=values, state="readonly", width=24).grid(
            row=row, column=1, sticky="w", pady=(10, 0)
        )

    def _check(self, row: int, key: str, label: str) -> None:
        var = tk.BooleanVar()
        self.vars[key] = var
        ttk.Checkbutton(self, text=label, variable=var).grid(
            row=row, column=1, sticky="w", pady=(8, 0)
        )

    def _browse(self, var: tk.StringVar, kind: str) -> None:
        if kind == "dir":
            chosen = filedialog.askdirectory(initialdir=var.get() or str(Path.home()))
        else:
            chosen = filedialog.askopenfilename(initialdir=var.get() or str(Path.home()))
        if chosen:
            var.set(chosen)

    # -------------------------------------------------------------------- layout

    def _build_directories(self) -> None:
        ttk.Label(self, text="Folders", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self._entry(1, "download_dir", "Downloads are saved in", "dir")
        self._entry(2, "audio_dir", "Audio files are saved in", "dir")

    def _build_formats(self) -> None:
        ttk.Label(self, text="Formats", style="Title.TLabel").grid(row=3, column=0, sticky="w", pady=(24, 0))
        self._entry(4, "filename_template", "Name of the downloaded files")
        self._choice(5, "audio_format", "Audio format", AUDIO_FORMATS)
        self._choice(6, "merge_output_format", "Videos are merged into", ("mkv", "mp4", "webm"))
        self._check(7, "embed_metadata", "Write the metadata into the file")
        self._check(8, "embed_thumbnail", "Embed the thumbnail")
        self._check(9, "write_subtitles", "Download the subtitles")
        self._entry(10, "subtitle_langs", "Languages of the subtitles")

    def _build_network(self) -> None:
        ttk.Label(self, text="Network", style="Title.TLabel").grid(
            row=11, column=0, sticky="w", pady=(24, 0)
        )
        self._entry(12, "proxy", "Proxy")
        self._entry(13, "rate_limit", "Maximum speed, for example 2M")
        self._entry(14, "cookies_file", "Cookies file", "file")
        self._entry(15, "concurrent_fragments", "Fragments that are downloaded at once")
        self._entry(16, "max_concurrent_downloads", "Downloads that run at the same time")
        self._entry(17, "extra_args", "Extra arguments for yt-dlp")

    def _build_instagram(self) -> None:
        ttk.Label(self, text="Instagram", style="Title.TLabel").grid(
            row=20, column=0, sticky="w", pady=(24, 0)
        )
        self._entry(21, "instagram_download_dir", "The media is saved in", "dir")
        self._entry(22, "instagram_session_file", "Session file", "file")
        self._entry(23, "instagram_profile_limit", "How many posts of a profile are downloaded")

    def _build_appearance(self) -> None:
        ttk.Label(self, text="Appearance", style="Title.TLabel").grid(
            row=18, column=0, sticky="w", pady=(24, 0)
        )
        self._choice(24, "theme", "Theme", THEMES)

    # ------------------------------------------------------------------- actions

    def load(self) -> None:
        """Fills the form with the current settings."""
        settings = self.app.settings
        for key, var in self.vars.items():
            value = getattr(settings, key, "")
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            else:
                var.set(str(value))

    def save(self) -> None:
        """Writes the form back into the settings."""
        settings = self.app.settings
        for key, var in self.vars.items():
            value = var.get()
            current = getattr(settings, key, "")
            if isinstance(current, bool):
                setattr(settings, key, bool(value))
            elif isinstance(current, int):
                try:
                    setattr(settings, key, int(value))
                except (TypeError, ValueError):
                    pass
            else:
                setattr(settings, key, str(value))
        settings.save()
        self.app.apply_theme()
        self.app.show_message("The settings have been saved.")

    def open_data_dir(self) -> None:
        from .history_tab import open_path

        from ..config import data_dir

        open_path(str(data_dir()))
