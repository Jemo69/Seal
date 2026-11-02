"""The tab that downloads photos and videos from instagram."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

from ..instagram import InstagramClient, InstagramError, InstagramItem, InstagramTarget, parse_link
from .theme import Palette
from .widgets import Card, load_thumbnail

if TYPE_CHECKING:  # pragma: no cover
    from .app import MainWindow


class MediaCard(ttk.Frame):
    """One photo or video of a post."""

    def __init__(self, master: tk.Misc, app: "MainWindow", item: InstagramItem, index: int) -> None:
        super().__init__(master, style="Surface.TFrame", padding=(12, 10))
        self.app = app
        self.item = item
        self.index = index
        self.palette: Palette = app.palette
        self.columnconfigure(1, weight=1)

        self.preview = ttk.Label(self, text="")
        self.preview.grid(row=0, column=0, padx=(0, 12), sticky="nw")

        kind = "Video" if item.is_video else "Photo"
        ttk.Label(self, text=f"{kind} • {item.post_code}", style="Subtitle.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        description = item.description or item.username or ""
        ttk.Label(self, text=description, style="Muted.TLabel", wraplength=460).grid(
            row=1, column=1, sticky="w", pady=(4, 8)
        )
        self.button = ttk.Button(self, text="Download", command=self._download, width=12)
        self.button.grid(row=2, column=1, sticky="w")

    def _download(self) -> None:
        self.button.configure(state="disabled", text="Working...")
        self.app.download_instagram_item(self.item, self.index, self)


class InstagramTab(ttk.Frame):
    """Lets the user paste an instagram link and save the media."""

    def __init__(self, master: tk.Misc, app: "MainWindow") -> None:
        super().__init__(master, padding=20)
        self.app = app
        self.palette: Palette = app.palette
        self.items: list[InstagramItem] = []
        self.cards: list[MediaCard] = []
        self.columnconfigure(0, weight=1)

        self._build_input()
        self._build_result()

    # -------------------------------------------------------------------- input

    def _build_input(self) -> None:
        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Paste an instagram link", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(frame, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, sticky="ew")
        self.url_entry.bind("<Return>", lambda _event: self.fetch())

        self.fetch_button = ttk.Button(frame, text="Fetch", command=self.fetch)
        self.fetch_button.grid(row=1, column=1, padx=(10, 0))

        self.hint_label = ttk.Label(
            self,
            text=(
                "Posts, reels, igtv and profiles are supported. Stories and private posts need a "
                "session file, see the settings."
            ),
            style="Muted.TLabel",
            wraplength=640,
        )
        self.hint_label.grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _build_result(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=2, column=0, sticky="ew", pady=(16, 8))
        header.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(header, text="", style="Title.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")

        self.download_all_button = ttk.Button(
            header, text="Download all", style="Accent.TButton", command=self.download_all, state="disabled"
        )
        self.download_all_button.grid(row=0, column=1)

        self.result = ttk.Frame(self)
        self.result.grid(row=3, column=0, sticky="ew")
        self.result.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------ actions

    def fetch(self) -> None:
        """Reads the media of the pasted link."""
        url = self.url_var.get().strip()
        target = parse_link(url)
        if target is None:
            self.app.show_error("Please paste a link of instagram.com.")
            return

        self.fetch_button.configure(state="disabled")
        self.title_label.configure(text="Reading the media...")

        def worker() -> None:
            client = InstagramClient(session_file=self.app.settings.instagram_session_file)
            try:
                items = client.fetch(target, limit=self.app.settings.instagram_profile_limit)
                self.app.events.put(("instagram", (target, items, "")))
            except InstagramError as error:
                self.app.events.put(("instagram", (target, [], str(error))))
            except Exception as error:  # noqa: BLE001 - the message is shown to the user
                self.app.events.put(("instagram", (target, [], str(error))))

        threading.Thread(target=worker, daemon=True).start()

    def show_items(self, target: InstagramTarget, items: list[InstagramItem]) -> None:
        """Fills the tab with the media that was found."""
        self.fetch_button.configure(state="normal")
        self.items = items
        self._clear_cards()

        if not items:
            self.title_label.configure(text=f"Nothing found for {target.label}")
            self.download_all_button.configure(state="disabled")
            return

        self.title_label.configure(text=f"{len(items)} media from {target.label}")
        self.download_all_button.configure(state="normal")

        for index, item in enumerate(items):
            card = MediaCard(self.result, self.app, item, index)
            card.grid(row=index, column=0, sticky="ew", pady=(0, 8))
            self.cards.append(card)
            thumbnail = load_thumbnail(item.thumbnail, 96, 96, self.palette)
            if thumbnail is not None:
                card.preview.configure(image=thumbnail)

    def _clear_cards(self) -> None:
        for card in self.cards:
            card.destroy()
        self.cards = []

    def download_all(self) -> None:
        """Downloads every media of the post."""
        if not self.items:
            return
        self.download_all_button.configure(state="disabled")
        self.app.download_instagram_items(self.items)

    def item_finished(self, index: int, success: bool) -> None:
        """Called when a single download is done."""
        if 0 <= index < len(self.cards):
            card = self.cards[index]
            if success:
                card.button.configure(text="Saved", state="disabled")
            else:
                card.button.configure(text="Try again", state="normal")
