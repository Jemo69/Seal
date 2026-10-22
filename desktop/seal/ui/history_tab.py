"""The tab that shows the files that were downloaded before."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

from ..history import HistoryEntry
from .theme import Palette

if TYPE_CHECKING:  # pragma: no cover
    from .app import MainWindow


def open_path(path: str) -> None:
    """Opens a file or a folder with the default application."""
    target = Path(path)
    if not target.exists():
        return
    try:
        if sys.platform == "win32":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except OSError:
        pass


class HistoryTab(ttk.Frame):
    """A list of the downloaded files."""

    def __init__(self, master: tk.Misc, app: "MainWindow") -> None:
        super().__init__(master, padding=20)
        self.app = app
        self.palette: Palette = app.palette
        self._entries: dict[str, HistoryEntry] = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Download history", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Clear", command=self.clear).pack(side="right")

        columns = ("title", "uploader", "path")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("title", text="Title")
        self.tree.heading("uploader", text="Channel")
        self.tree.heading("path", text="File")
        self.tree.column("title", width=280, anchor="w")
        self.tree.column("uploader", width=140, anchor="w")
        self.tree.column("path", width=380, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", lambda _event: self.open_selected())

        buttons = ttk.Frame(self)
        buttons.grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Button(buttons, text="Open file", command=self.open_selected).pack(side="left")
        ttk.Button(buttons, text="Open folder", command=self.open_folder).pack(side="left", padx=8)
        ttk.Button(buttons, text="Remove", style="Danger.TButton", command=self.remove_selected).pack(
            side="left"
        )

        self.refresh()

    def refresh(self) -> None:
        """Reloads the list."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._entries = {}
        for index, entry in enumerate(self.app.history.entries):
            # The same file can be downloaded more than once, the id of the row is therefore
            # not the path of the file.
            item_id = f"entry_{index}"
            self._entries[item_id] = entry
            self.tree.insert(
                "", "end", iid=item_id, values=(entry.title, entry.uploader, entry.path)
            )

    def _selected(self) -> HistoryEntry | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._entries.get(selection[0])

    def open_selected(self) -> None:
        entry = self._selected()
        if entry:
            open_path(entry.path)

    def open_folder(self) -> None:
        entry = self._selected()
        if entry:
            open_path(str(Path(entry.path).parent))

    def remove_selected(self) -> None:
        entry = self._selected()
        if entry:
            self.app.history.remove(entry)
            self.refresh()

    def clear(self) -> None:
        self.app.history.clear()
        self.refresh()
