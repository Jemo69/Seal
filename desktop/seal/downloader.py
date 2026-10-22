"""The yt-dlp integration.

Every download runs in its own thread, the user interface is updated through the callbacks that
are passed to the [DownloadManager].
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Callable

from .config import Settings
from .logging_setup import YtdlpLogger, log, log_exception
from .models import Format, Task, TaskState, VideoInfo

try:  # pragma: no cover - the import depends on the environment
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None  # type: ignore[assignment]


class YtdlpNotInstalled(Exception):
    """Raised when the yt-dlp module is not available."""


class DownloadCancelled(Exception):
    """Raised inside the progress hook to stop a running download."""


def is_available() -> bool:
    """Whether yt-dlp is installed."""
    return yt_dlp is not None


def version() -> str:
    """The version of the installed yt-dlp."""
    if yt_dlp is None:
        return ""
    return getattr(yt_dlp.version, "__version__", "")


def _require_ytdlp() -> None:
    if yt_dlp is None:
        raise YtdlpNotInstalled(
            "yt-dlp is not installed, run 'pip install -r requirements.txt' to install it"
        )


def format_size(num_bytes: float | None) -> str:
    """Formats a number of bytes the way a downloader shows them."""
    if not num_bytes:
        return ""
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return ""


def format_duration(seconds: float | None) -> str:
    """Formats a number of seconds."""
    if not seconds:
        return ""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class DownloadManager:
    """Runs the downloads and keeps track of them."""

    def __init__(
        self,
        settings: Settings,
        on_update: Callable[[Task], None] | None = None,
        on_finished: Callable[[Task], None] | None = None,
    ) -> None:
        self.settings = settings
        self.on_update = on_update or (lambda task: None)
        self.on_finished = on_finished or (lambda task: None)
        self._tasks: dict[str, Task] = {}
        self._cancelled: set[str] = set()
        self._lock = threading.Lock()

    # -------------------------------------------------------------------- tasks

    @property
    def tasks(self) -> list[Task]:
        with self._lock:
            return list(self._tasks.values())

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    # ------------------------------------------------------------------- options

    def _base_options(self, audio_only: bool = False, quick: bool = False) -> dict[str, Any]:
        settings = self.settings
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "consoletitle": False,
            "windowsfilenames": True,
            # "only_download" is truthy, yt-dlp would swallow every error of the extraction
            # with it. The information of a link has to fail loudly.
            "ignoreerrors": "only_download" if not quick else False,
            # A link that cannot be read should not keep the user waiting for minutes.
            "retries": 2 if quick else 5,
            "fragment_retries": 2 if quick else 5,
            "socket_timeout": min(settings.socket_timeout, 15) if quick else settings.socket_timeout,
            "concurrent_fragment_downloads": max(1, settings.concurrent_fragments),
            "outtmpl": {"default": settings.filename_template},
            "paths": {"home": str(settings.target_dir(audio_only))},
            "logger": YtdlpLogger(),
        }
        if settings.proxy:
            options["proxy"] = settings.proxy
        if settings.rate_limit:
            options["ratelimit"] = _parse_rate(settings.rate_limit)
        if settings.cookies_file and Path(settings.cookies_file).exists():
            options["cookiefile"] = settings.cookies_file
        if settings.cookies_from_browser:
            # Many sites ask for a login, the cookies of the browser solve that.
            options["cookiesfrombrowser"] = (settings.cookies_from_browser, None, None, None)
        if settings.extra_args:
            options.update(_parse_extra_args(settings.extra_args))
        return options

    def _download_options(self, task: Task) -> dict[str, Any]:
        settings = self.settings
        options = self._base_options(audio_only=task.audio_only)

        if task.audio_only:
            options["format"] = task.format_id or "bestaudio/best"
            postprocessors: list[dict[str, Any]] = []
            if settings.audio_format and settings.audio_format != "best":
                postprocessors.append(
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": settings.audio_format,
                    }
                )
            if postprocessors:
                options["postprocessors"] = postprocessors
        else:
            options["format"] = task.format_id or "bestvideo*+bestaudio/best"
            postprocessors = []
            if settings.merge_output_format:
                postprocessors.append(
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": settings.merge_output_format,
                    }
                )
            if postprocessors:
                options["postprocessors"] = postprocessors

        if settings.embed_metadata:
            options["postprocessors"] = options.get("postprocessors", []) + [
                {"key": "FFmpegMetadata", "add_chapters": True, "add_metadata": True}
            ]
        if settings.embed_thumbnail:
            options["postprocessors"] = options.get("postprocessors", []) + [
                {"key": "EmbedThumbnail", "already_have_thumbnail": False}
            ]
        if settings.write_subtitles:
            options["writesubtitles"] = True
            options["writeautomaticsub"] = settings.write_auto_subs
            if settings.subtitle_langs:
                options["subtitleslangs"] = settings.subtitle_langs
        return options

    def _info_options(self) -> dict[str, Any]:
        options = self._base_options(quick=True)
        options["extract_flat"] = "in_playlist"
        options["skip_download"] = True
        return options

    # ------------------------------------------------------------------ fetching

    def fetch_info(
        self,
        url: str,
        on_done: Callable[[VideoInfo | None, str], None],
        on_progress: Callable[[str], None] | None = None,
    ) -> threading.Thread:
        """Fetches the information of a video in a background thread."""

        def worker() -> None:
            _require_ytdlp()
            log(f"reading the information of {url}")
            result: list[tuple[Any, str]] = []

            def extract() -> None:
                try:
                    with yt_dlp.YoutubeDL(self._info_options()) as ydl:
                        result.append((ydl.extract_info(url, download=False), ""))
                except Exception as error:  # noqa: BLE001 - the message is shown to the user
                    log_exception(f"the information of {url} could not be read")
                    result.append((None, str(error)))

            thread = threading.Thread(target=extract, daemon=True)
            thread.start()
            thread.join(timeout=INFO_TIMEOUT)
            if thread.is_alive():
                on_done(
                    None,
                    "The website did not answer in time. The connection to the internet might be "
                    "blocked, a proxy could help.",
                )
                return

            info, error = result[0] if result else (None, "No information found")
            if info is None:
                on_done(None, friendly_error(error or "No information found"))
                return
            on_done(VideoInfo.from_info(url, info), "")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

    # ---------------------------------------------------------------- downloading

    def enqueue(self, task: Task) -> None:
        """Starts a download."""
        with self._lock:
            self._tasks[task.task_id] = task
        thread = threading.Thread(target=self._run_download, args=(task,), daemon=True)
        thread.start()

    def cancel(self, task_id: str) -> None:
        """Cancels a running download."""
        with self._lock:
            self._cancelled.add(task_id)
            task = self._tasks.get(task_id)
        if task and not task.state.is_finished:
            task.state = TaskState.CANCELED
            task.error = "Canceled"
            self.on_update(task)
            self.on_finished(task)

    def remove(self, task_id: str) -> None:
        """Removes a task from the list."""
        with self._lock:
            self._tasks.pop(task_id, None)
            self._cancelled.discard(task_id)

    def _is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._cancelled

    def _run_download(self, task: Task) -> None:
        _require_ytdlp()
        options = self._download_options(task)
        log(f"starting the download of {task.url}")

        def progress_hook(data: dict[str, Any]) -> None:
            if self._is_cancelled(task.task_id):
                raise DownloadCancelled()
            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                downloaded = data.get("downloaded_bytes") or 0
                task.progress = (downloaded / total) if total else 0.0
                task.speed = format_size(data.get("speed"))
                task.eta = format_duration(data.get("eta"))
                task.size = format_size(total)
                task.state = TaskState.DOWNLOADING
                self.on_update(task)
            elif status == "finished":
                task.progress = 1.0
                task.state = TaskState.PROCESSING
                self.on_update(task)

        def postprocessor_hook(data: dict[str, Any]) -> None:
            if data.get("status") == "started":
                task.state = TaskState.PROCESSING
                self.on_update(task)

        options["progress_hooks"] = [progress_hook]
        options["postprocessor_hooks"] = [postprocessor_hook]

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(task.url, download=True)
            if self._is_cancelled(task.task_id):
                task.state = TaskState.CANCELED
                task.error = "Canceled"
            else:
                task.state = TaskState.COMPLETED
                task.progress = 1.0
                task.filename = _downloaded_path(info)
        except DownloadCancelled:
            task.state = TaskState.CANCELED
            task.error = "Canceled"
        except Exception as error:  # noqa: BLE001 - the message is shown to the user
            log_exception(f"the download of {task.url} failed")
            task.state = TaskState.ERROR
            task.error = str(error)
        self.on_update(task)
        self.on_finished(task)


INFO_TIMEOUT = 90


def friendly_error(error: str) -> str:
    """Turns the message of yt-dlp into something the user can act on."""
    lowered = error.lower()
    if "sign in to confirm" in lowered or "login required" in lowered:
        return (
            "The website asks for a login for this video.\n\n"
            "Choose the browser your are signed in with in the settings "
            "(Cookies from browser) and try again."
        )
    if "private video" in lowered or "this video is private" in lowered:
        return "This video is private, a login is needed to see it."
    if "unsupported url" in lowered or "no video formats" in lowered:
        return "The website does not offer any video for this link."
    if "timed out" in lowered or "timed out" in lowered:
        return (
            "The website did not answer in time. The connection to the internet might be "
            "blocked, a proxy could help."
        )
    return error


def _downloaded_path(info: dict[str, Any] | None) -> str:
    """The path of the file yt-dlp wrote."""
    if not info:
        return ""
    if info.get("filepath"):
        return str(info["filepath"])
    requested = info.get("requested_downloads") or []
    for entry in requested:
        if entry.get("filepath"):
            return str(entry["filepath"])
    return str(info.get("_filename") or "")


def _parse_rate(value: str) -> int:
    """Parses a rate limit like '2M' into bytes per second."""
    value = value.strip().upper()
    if not value:
        return 0
    multiplier = 1
    if value.endswith("K"):
        multiplier, value = 1024, value[:-1]
    elif value.endswith("M"):
        multiplier, value = 1024 * 1024, value[:-1]
    elif value.endswith("G"):
        multiplier, value = 1024 * 1024 * 1024, value[:-1]
    try:
        return int(float(value) * multiplier)
    except ValueError:
        return 0


def _parse_extra_args(value: str) -> dict[str, Any]:
    """Turns the extra arguments of the settings into yt-dlp options."""
    import shlex

    options: dict[str, Any] = {}
    try:
        tokens = shlex.split(value)
    except ValueError:
        tokens = value.split()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            index += 1
            continue
        name = token[2:].replace("-", "_")
        if index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
            options[name] = tokens[index + 1]
            index += 2
        else:
            options[name] = True
            index += 1
    return options
