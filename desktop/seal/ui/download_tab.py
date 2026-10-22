"""The tab that starts a new download."""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Callable

from ..models import Format, Task, TaskState, VideoInfo
from .theme import Palette
from .widgets import Card, load_thumbnail

if TYPE_CHECKING:  # pragma: no cover
    from .app import MainWindow

URL_PATTERN = re.compile(r"https?://\S+")


def extract_urls(text: str) -> list[str]:
    """Returns every url of the given text."""
    return URL_PATTERN.findall(text.strip())


class DownloadTab(ttk.Frame):
    """Lets the user paste a link and pick a format."""

    def __init__(self, master: tk.Misc, app: "MainWindow") -> None:
        super().__init__(master, padding=20)
        self.app = app
        self.palette: Palette = app.palette
        self.info: VideoInfo | None = None
        self._thumbnail: tk.PhotoImage | None = None
        self._formats: list[tuple[str, str]] = []

        self.columnconfigure(0, weight=1)

        self._build_input()
        self._build_card()
        self._build_options()

    # -------------------------------------------------------------------- input

    def _build_input(self) -> None:
        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Paste a link", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(frame, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, sticky="ew")
        self.url_entry.bind("<Return>", lambda _event: self.fetch())

        self.fetch_button = ttk.Button(frame, text="Fetch", command=self.fetch)
        self.fetch_button.grid(row=1, column=1, padx=(10, 0))

        self.status = ttk.Label(self, text="Reading the information...", style="Muted.TLabel")
        self.status.grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.status.grid_remove()

        ttk.Label(
            self,
            text="Several links can be pasted at once, the settings say how many of them "
            "are downloaded at the same time.",
            style="Muted.TLabel",
            wraplength=640,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

    # --------------------------------------------------------------------- card

    def _build_card(self) -> None:
        self.card = Card(self, self.palette)
        self.card.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        self.card.columnconfigure(1, weight=1)

        self.thumbnail_label = ttk.Label(self.card, text="No preview")
        self.thumbnail_label.grid(row=0, column=0, padx=(0, 16), sticky="nw")

        self.title_label = ttk.Label(self.card, text="", style="Title.TLabel", wraplength=520)
        self.title_label.grid(row=0, column=1, sticky="w")
        self.meta_label = ttk.Label(self.card, text="", style="Muted.TLabel")
        self.meta_label.grid(row=1, column=1, sticky="w", pady=(4, 12))

        ttk.Label(self.card, text="Format", style="Muted.TLabel").grid(
            row=2, column=1, sticky="w"
        )
        self.format_var = tk.StringVar(value="Best quality")
        self.format_box = ttk.Combobox(
            self.card, textvariable=self.format_var, state="readonly", width=48
        )
        self.format_box.grid(row=3, column=1, sticky="ew", pady=(4, 0))

        self.download_button = ttk.Button(
            self.card, text="Download", style="Accent.TButton", command=self.download, state="disabled"
        )
        self.download_button.grid(row=4, column=1, sticky="w", pady=(16, 0))

        self.card.grid_remove()

    def _build_options(self) -> None:
        options = ttk.Frame(self)
        options.grid(row=3, column=0, sticky="w", pady=(12, 0))

        self.audio_only_var = tk.BooleanVar(value=False)
        self.playlist_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text="Audio only", variable=self.audio_only_var).grid(
            row=0, column=0, padx=(0, 16)
        )
        ttk.Checkbutton(options, text="Whole playlist", variable=self.playlist_var).grid(
            row=0, column=1
        )
        # The formats of the box depend on the sound, only the audio formats are offered
        # when the user asks for the sound alone.
        self.audio_only_var.trace_add("write", lambda *_: self._refresh_formats())

    # ------------------------------------------------------------------ actions

    def fetch(self) -> None:
        """Reads the information of the pasted link."""
        urls = extract_urls(self.url_var.get())
        if not urls:
            self.app.show_error("Please paste a link first.")
            return
        if len(urls) > 1:
            self.app.queue_urls(urls)
            return

        url = urls[0]
        self.fetch_button.configure(state="disabled")
        self.status.configure(text="Reading the information...")
        self.status.grid()

        # The callback runs in a download thread, the user interface is updated by the
        # main loop of the application.
        def on_done(info: VideoInfo | None, error: str) -> None:
            self.app.events.put(("info", (info, error)))

        self.app.manager.fetch_info(url, on_done)

    def show_info(self, info: VideoInfo) -> None:
        """Fills the card with the information of a video."""
        self.info = info
        self.status.grid_remove()
        self.title_label.configure(text=info.title)
        details = [part for part in (info.uploader, info.duration_text) if part]
        if info.is_playlist:
            details.append(f"{info.playlist_count} videos")
        self.meta_label.configure(text="  •  ".join(details))

        self._refresh_formats()

        thumbnail = load_thumbnail(info.thumbnail, 220, 124, self.palette)
        if thumbnail is not None:
            self._thumbnail = thumbnail
            self.thumbnail_label.configure(image=thumbnail, text="")

        self.download_button.configure(state="normal")
        self.card.grid()

    def _refresh_formats(self) -> None:
        """Fills the format box with the formats that fit the chosen options."""
        if self.info is None:
            return
        self._formats = self._format_list(self.info, self.audio_only_var.get())
        self.format_box.configure(values=[label for label, _ in self._formats])
        if self._formats:
            self.format_var.set(self._formats[0][0])

    def _format_list(self, info: VideoInfo, audio_only: bool = False) -> list[tuple[str, str]]:
        """Builds the entries of the format selection."""
        entries: list[tuple[str, str]] = []
        if info.is_playlist:
            entries.append(("Best quality", "bestvideo*+bestaudio/best"))
            return entries

        audio = [fmt for fmt in info.formats if not fmt.has_video and fmt.has_audio]

        if not audio_only:
            video = [fmt for fmt in info.formats if fmt.has_video]
            video.sort(key=lambda fmt: (fmt.height, fmt.tbr or 0), reverse=True)
            seen: set[str] = set()
            for fmt in video:
                if fmt.height and fmt.height in seen:
                    continue
                if fmt.height:
                    seen.add(fmt.height)
                entries.append((f"Video • {fmt.label}", fmt.selector))

            if not entries:
                entries.append(("Best quality", "bestvideo*+bestaudio/best"))
        else:
            entries.append(("Best audio", "bestaudio/best"))

        for fmt in sorted(audio, key=lambda fmt: fmt.tbr or 0, reverse=True)[:3]:
            entries.append((f"Audio • {fmt.ext} • {fmt.tbr or 0:.0f} kbps", fmt.format_id))
        return entries

    def download(self) -> None:
        """Adds the download to the queue."""
        if self.info is None:
            return
        url = self.info.url
        format_id = ""
        # The index is used and not the label, two formats can have the same label.
        index = self.format_box.current()
        if 0 <= index < len(self._formats):
            format_id = self._formats[index][1]

        task = Task(
            url=url,
            title=self.info.title,
            audio_only=self.audio_only_var.get(),
            playlist=self.playlist_var.get(),
            is_playlist=self.info.is_playlist,
            format_id=format_id,
        )
        self.app.enqueue(task)
        self.app.select_tab("queue")
