"""Starts the application.

    python -m seal            starts the window
    python -m seal --version  prints the version
    python -m seal --check    verifies that everything is in place
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)

    if "--version" in arguments or "-v" in arguments:
        from seal import APP_NAME, __version__

        print(f"{APP_NAME} {__version__}")
        return 0

    if "--check" in arguments:
        return _self_check()

    from seal.ui.app import run

    run()
    return 0


def _self_check() -> int:
    """Verifies that the application can be used on this machine."""
    from seal.config import Settings, data_dir
    from seal.downloader import is_available, version

    print(f"data directory: {data_dir()}")
    settings = Settings.load()
    print(f"download directory: {settings.download_dir}")
    print(f"audio directory: {settings.audio_dir}")

    if is_available():
        print(f"yt-dlp {version()}")
    else:
        print("yt-dlp is not installed, run 'pip install -r requirements.txt'", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
