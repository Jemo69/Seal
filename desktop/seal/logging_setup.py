"""The log file of the application.

Every request to yt-dlp and every error is written to a log file, the support of a downloader
is much easier with it.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

from .config import data_dir

LOG_NAME = "seal.log"

_configured = False
_configure_lock = threading.Lock()


def log_path() -> Path:
    """The file the log is written to."""
    return data_dir() / LOG_NAME


def _configure() -> logging.Logger:
    """Creates the logger, it is only done once."""
    global _configured
    logger = logging.getLogger("seal")
    with _configure_lock:
        if _configured:
            return logger

        path = log_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(path, encoding="utf-8")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
            )
            logger.addHandler(handler)
        except OSError:
            # The log file is a help, the application works without it.
            pass
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        _configured = True
    return logger


def get_logger(name: str = "seal") -> logging.Logger:
    """The logger of the application."""
    _configure()
    return logging.getLogger(name if name.startswith("seal") else f"seal.{name}")


def log(message: str, level: int = logging.INFO) -> None:
    """Writes a line into the log file."""
    get_logger().log(level, message)


def log_exception(message: str) -> None:
    """Writes an error and its traceback into the log file."""
    get_logger().exception(message)


class YtdlpLogger:
    """Sends the output of yt-dlp into the log file."""

    def __init__(self) -> None:
        self.logger = get_logger("yt-dlp")
        # yt-dlp hides the errors of an extraction, the last one is kept so that the
        # user can be told what went wrong.
        self.last_error = ""

    def debug(self, message: str) -> None:
        if message.startswith("[debug] "):
            return
        self.logger.debug(message)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.last_error = message
        self.logger.error(message)
