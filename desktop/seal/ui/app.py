"""The main window of the application."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from .. import APP_NAME, __version__
from ..config import Settings
from ..downloader import DownloadManager, is_available, version
from ..history import History, HistoryEntry
from ..logging_setup import log_exception, log_path
from ..instagram import InstagramClient, InstagramItem, InstagramTarget
from ..models import Task, TaskState
from .download_tab import DownloadTab
from .history_tab import HistoryTab
from .instagram_tab import InstagramTab
from .queue_tab import QueueTab
from .settings_tab import SettingsTab
from .theme import DARK, LIGHT, Palette, apply_theme


class MainWindow(tk.Tk):
    """The window of the application."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {__version__}")
        self.geometry("940x680")
        self.minsize(760, 520)

        self.settings = Settings.load()
        self.history = History()
        self.palette = self._palette()
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()

        apply_theme(self, self.palette)
        self._build_header()
        self._build_tabs()

        self.manager = DownloadManager(
            self.settings,
            on_update=self._on_task_update,
            on_finished=self._on_task_finished,
        )

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._process_events)
        self._show_startup_message()

    # -------------------------------------------------------------------- layout

    def _palette(self) -> Palette:
        theme = self.settings.theme
        if theme == "light":
            return LIGHT
        if theme == "dark":
            return DARK
        return LIGHT

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(20, 16, 20, 8))
        header.pack(fill="x")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=APP_NAME, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        subtitle = ttk.Label(header, text="Video and audio downloader", style="Muted.TLabel")
        subtitle.grid(row=1, column=0, sticky="w")

        self.theme_button = ttk.Button(header, text="Dark mode", command=self.toggle_theme, width=12)
        self.theme_button.grid(row=0, column=1, rowspan=2, padx=(0, 8))

        ytdlp_text = f"yt-dlp {version()}" if is_available() else "yt-dlp is not installed"
        ttk.Label(header, text=ytdlp_text, style="Muted.TLabel").grid(row=0, column=2, rowspan=2)

    def _build_tabs(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.download_tab = DownloadTab(self.notebook, self)
        self.instagram_tab = InstagramTab(self.notebook, self)
        self.queue_tab = QueueTab(self.notebook, self)
        self.history_tab = HistoryTab(self.notebook, self)
        self.settings_tab = SettingsTab(self.notebook, self)

        self.notebook.add(self.download_tab, text="Download")
        self.notebook.add(self.instagram_tab, text="Instagram")
        self.notebook.add(self.queue_tab, text="Queue")
        self.notebook.add(self.history_tab, text="History")
        self.notebook.add(self.settings_tab, text="Settings")

        self.status_var = tk.StringVar()
        status = ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", padding=(20, 0, 20, 10))
        status.pack(fill="x")

    # -------------------------------------------------------------------- actions

    def toggle_theme(self) -> None:
        """Switches between the light and the dark theme."""
        self.settings.theme = "dark" if self.palette is LIGHT else "light"
        self.settings.save()
        self.apply_theme()

    def apply_theme(self) -> None:
        """Applies the current theme to every widget."""
        self.palette = self._palette()
        apply_theme(self, self.palette)
        self.theme_button.configure(
            text="Light mode" if self.palette is DARK else "Dark mode"
        )

    def select_tab(self, name: str) -> None:
        """Switches to the tab with the given name."""
        for index, tab in enumerate(self.notebook.tabs()):
            if str(self.notebook.tab(tab, "text")).lower() == name.lower():
                self.notebook.select(index)
                return

    def show_error(self, message: str) -> None:
        """Shows an error message."""
        messagebox.showerror(
            APP_NAME, f"{message}\n\nThe details are written to {log_path()}", parent=self
        )

    def show_message(self, message: str) -> None:
        """Shows a short message in the status bar."""
        self.status_var.set(message)
        self.after(4000, lambda: self.status_var.set(""))

    def enqueue(self, task: Task) -> None:
        """Adds a download to the queue."""
        self.queue_tab.add_task(task)
        self.manager.enqueue(task)
        self.show_message("The download has been added to the queue.")

    def download_instagram_items(
        self, items: list[InstagramItem], start_index: int = 0
    ) -> None:
        """Downloads every media of an instagram post."""

        def worker() -> None:
            client = InstagramClient(session_file=self.settings.instagram_session_file)
            target_dir = Path(self.settings.instagram_download_dir)
            for offset, item in enumerate(items):
                index = start_index + offset
                try:
                    path = client.download(item, target_dir)
                except Exception as error:  # noqa: BLE001 - the message is shown to the user
                    self.events.put(("instagram_item", (index, False, str(error))))
                    continue
                self.events.put(("instagram_item", (index, True, str(path))))
                self.history.add(
                    HistoryEntry(
                        title=item.description or item.post_code or "Instagram",
                        url=item.media_url,
                        path=str(path),
                        uploader=item.username,
                    )
                )

        threading.Thread(target=worker, daemon=True).start()
        self.show_message("The media is downloaded in the background.")

    def download_instagram_item(
        self, item: InstagramItem, index: int, card: object
    ) -> None:
        """Downloads a single media of an instagram post."""
        self.download_instagram_items([item], start_index=index)

    def queue_urls(self, urls: list[str]) -> None:
        """Adds every url of the list to the queue."""
        for url in urls:
            self.enqueue(Task(url=url, title=url))
        self.select_tab("queue")

    # --------------------------------------------------------------------- events

    def _on_task_update(self, task: Task) -> None:
        self.events.put(("update", task))

    def _on_task_finished(self, task: Task) -> None:
        self.events.put(("finished", task))

    def _process_events(self) -> None:
        """Moves the updates of the download threads into the user interface.

        The loop is never interrupted, a single broken update must not freeze the whole
        application.
        """
        try:
            while True:
                kind, payload = self.events.get_nowait()
                self._handle_event(kind, payload)
        except queue.Empty:
            pass
        except Exception:  # noqa: BLE001 - the loop has to keep running
            log_exception("an update could not be processed")
        finally:
            self.after(80, self._process_events)

    def _handle_event(self, kind: str, payload: Any) -> None:
        """Handles a single update of a download thread."""
        if kind == "update":
            self.queue_tab.update_task(payload)
        elif kind == "finished":
            self._on_finished(payload)
        elif kind == "info":
            self._on_info(payload)
        elif kind == "instagram":
            self._on_instagram(payload)
        elif kind == "connection":
            self._on_connection(payload)
        elif kind == "instagram_item":
            index, success, detail = payload
            self.instagram_tab.item_finished(index, success)
            if success:
                self.history_tab.refresh()

    def _on_info(self, payload: tuple) -> None:
        """Shows the information of a link that was read in the background."""
        info, error = payload
        self.download_tab.fetch_button.configure(state="normal")
        self.download_tab.status.grid_remove()
        if info is None:
            self.show_error(error or "The information could not be read.")
            return
        self.download_tab.show_info(info)

    def _on_connection(self, payload: tuple) -> None:
        """Shows the result of the connection test."""
        info, error, ytdlp_version = payload
        if info is None:
            self.show_error(
                f"The connection to the internet failed.\n\n{error}\n\n"
                f"The details are written to {log_path()}"
            )
            return
        self.show_message(f"The connection works, yt-dlp {ytdlp_version} is ready.")

    def _on_instagram(self, payload: tuple) -> None:
        """Shows the media of an instagram link."""
        target, items, error = payload
        if error:
            self.download_tab.fetch_button.configure(state="normal")
            self.instagram_tab.fetch_button.configure(state="normal")
            self.instagram_tab.show_items(target, [])
            self.show_error(error)
            return
        self.instagram_tab.show_items(target, items)

    def _on_finished(self, task: Task) -> None:
        if task.state is TaskState.COMPLETED:
            path = task.filename
            if path:
                self.history.add(
                    HistoryEntry(
                        title=task.title or task.url,
                        url=task.url,
                        path=path,
                    )
                )
                self.history_tab.refresh()
            self.show_message("The download has finished.")
        elif task.state is TaskState.ERROR:
            self.show_error(task.error or "The download has failed.")

    def _show_startup_message(self) -> None:
        if not is_available():
            self.show_error(
                "yt-dlp is not installed.\n\n"
                "Install it with:\n    pip install -r requirements.txt"
            )

    def _on_close(self) -> None:
        self.settings.save()
        self.destroy()


def run() -> None:
    """Starts the application."""
    window = MainWindow()
    window.mainloop()
