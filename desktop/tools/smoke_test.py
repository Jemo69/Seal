"""A manual smoke test of the user interface.

The script starts the application, reads a link, starts a download and writes a screenshot of
every tab. It needs a display and the ffmpeg or the xwd command to take the screenshots::

    python tools/smoke_test.py [url]
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seal.ui.app import MainWindow  # noqa: E402

DEFAULT_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
OUTPUT = Path(os.environ.get("SEAL_SMOKE_OUTPUT", "/tmp/seal-smoke"))


def window_id() -> str | None:
    """The id of the window of the application."""
    try:
        result = subprocess.run(
            ["xdotool", "search", "--name", "Seal"], capture_output=True, text=True
        )
    except FileNotFoundError:
        return None
    ids = [line for line in result.stdout.split() if line.strip()]
    return ids[-1] if ids else None


def shot(name: str) -> None:
    """Writes a screenshot of the window."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    wid = window_id()
    if not wid:
        print("no window found, the screenshot was skipped")
        return
    dump = OUTPUT / "window.xwd"
    subprocess.run(["xwd", "-id", wid, "-silent"], stdout=dump.open("wb"), check=False)
    subprocess.run(["convert", str(dump), str(OUTPUT / f"{name}.png")], check=False)
    print(f"saved {OUTPUT / f'{name}.png'}")


def pump(window: MainWindow, seconds: float = 1.0) -> None:
    """Runs the event loop of the application for a moment."""
    end = time.time() + seconds
    while time.time() < end:
        window.update()
        time.sleep(0.02)


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    window = MainWindow()
    window.update()
    window.lift()
    pump(window, 1.5)
    shot("01_start")

    window.download_tab.url_var.set(url)
    window.download_tab.fetch()
    pump(window, 8)
    shot("02_info")
    print("info:", window.download_tab.info.title if window.download_tab.info else None)

    window.download_tab.download()
    pump(window, 2)
    shot("03_queue")
    print("tasks:", [(task.title[:30], task.state.value) for task in window.manager.tasks])

    pump(window, 10)
    shot("04_downloading")
    for task in window.manager.tasks:
        print("task:", task.state.value, task.progress_percent, task.speed, task.eta)

    for name in ("instagram", "history", "settings"):
        window.select_tab(name)
        pump(window, 0.6)
        shot(f"05_{name}")

    window.destroy()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
