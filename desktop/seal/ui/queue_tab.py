"""The tab that shows the running downloads."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from ..models import Task, TaskState
from .theme import Palette
from .widgets import Card

if TYPE_CHECKING:  # pragma: no cover
    from .app import MainWindow


class TaskRow(ttk.Frame):
    """One download of the queue."""

    def __init__(self, master: tk.Misc, app: "MainWindow", task: Task) -> None:
        super().__init__(master, style="Surface.TFrame", padding=(14, 10))
        self.app = app
        self.task = task
        self.palette: Palette = app.palette
        self.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(self, text=task.title or task.url, style="Subtitle.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")

        self.state_label = ttk.Label(self, text="Queued", style="Muted.TLabel")
        self.state_label.grid(row=1, column=0, sticky="w", pady=(2, 8))

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.grid(row=2, column=0, sticky="ew")

        self.details_label = ttk.Label(self, text="", style="Muted.TLabel")
        self.details_label.grid(row=3, column=0, sticky="w", pady=(6, 0))

        self.cancel_button = ttk.Button(
            self, text="Cancel", style="Danger.TButton", command=self._cancel, width=10
        )
        self.cancel_button.grid(row=0, column=1, rowspan=4, padx=(12, 0))

        self.update(task)

    def _cancel(self) -> None:
        self.app.manager.cancel(self.task.task_id)

    def update(self, task: Task) -> None:
        """Refreshes the row with the state of the download."""
        self.task = task
        self.title_label.configure(text=task.title or task.url)
        self.state_label.configure(text=_state_text(task))
        self.progress.configure(value=task.progress_percent)

        details = []
        if task.size:
            details.append(task.size)
        if task.speed:
            details.append(task.speed)
        if task.eta:
            details.append(f"ETA {task.eta}")
        if task.error:
            details.append(task.error)
        self.details_label.configure(text="  •  ".join(details))

        if task.state.is_finished:
            self.cancel_button.configure(text="Remove", command=self._remove)
        else:
            self.cancel_button.configure(text="Cancel", command=self._cancel)

    def _remove(self) -> None:
        self.app.manager.remove(self.task.task_id)
        self.app.queue_tab.remove_row(self.task.task_id)


def _state_text(task: Task) -> str:
    if task.state is TaskState.QUEUED:
        return "Queued"
    if task.state is TaskState.DOWNLOADING:
        return f"Downloading • {task.progress_percent}%"
    if task.state is TaskState.PROCESSING:
        return "Processing"
    if task.state is TaskState.COMPLETED:
        return "Finished"
    if task.state is TaskState.CANCELED:
        return "Canceled"
    return "Failed"


class QueueTab(ttk.Frame):
    """Shows every download of this session."""

    def __init__(self, master: tk.Misc, app: "MainWindow") -> None:
        super().__init__(master, padding=20)
        self.app = app
        self.rows: dict[str, TaskRow] = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Downloads", style="Title.TLabel").pack(side="left")
        self.clear_button = ttk.Button(header, text="Clear finished", command=self.clear_finished)
        self.clear_button.pack(side="right")

        self.empty_label = ttk.Label(
            self, text="Nothing is downloading right now.", style="Muted.TLabel"
        )
        self.empty_label.grid(row=1, column=0, sticky="n")

        self.container = ttk.Frame(self)
        self.container.grid(row=1, column=0, sticky="new")
        self.container.columnconfigure(0, weight=1)

    def add_task(self, task: Task) -> None:
        """Adds a download to the list."""
        self.empty_label.grid_remove()
        row = TaskRow(self.container, self.app, task)
        self.rows[task.task_id] = row
        self._layout_rows()

    def _layout_rows(self) -> None:
        """Places the rows one below the other.

        The rows are placed again after a removal, otherwise a new row would land on the
        place of a row that was removed before it.
        """
        for index, row in enumerate(self.rows.values()):
            row.grid(row=index, column=0, sticky="ew", pady=(0, 8))

    def update_task(self, task: Task) -> None:
        """Refreshes a single download."""
        row = self.rows.get(task.task_id)
        if row is not None:
            row.update(task)

    def remove_row(self, task_id: str) -> None:
        """Removes a download from the list."""
        row = self.rows.pop(task_id, None)
        if row is not None:
            row.destroy()
        self._layout_rows()
        if not self.rows:
            self.empty_label.grid()

    def clear_finished(self) -> None:
        """Removes every download that is finished."""
        for task in self.app.manager.tasks:
            if task.state.is_finished:
                self.app.manager.remove(task.task_id)
                self.remove_row(task.task_id)
