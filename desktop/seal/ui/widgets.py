"""Small widgets that are used by more than one tab."""

from __future__ import annotations

import tkinter as tk
import urllib.request
from tkinter import ttk

from .theme import Palette


class ScrollableFrame(ttk.Frame):
    """A frame that can be scrolled, it holds its content in an inner frame."""

    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _on_scroll(self, first: str, last: str) -> None:
        self.scrollbar.set(first, last)

    def _on_inner_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not self._is_pointer_inside(event):
            return
        if getattr(event, "num", 0) == 4:
            self.canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", 0) == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _is_pointer_inside(self, event: tk.Event) -> bool:
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return False
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False


def load_thumbnail(url: str, width: int, height: int, palette: Palette) -> tk.PhotoImage | None:
    """Downloads a thumbnail and turns it into a photo image.

    Pillow is used when it is installed, it supports every image format. Without it only png
    images can be shown.
    """
    if not url:
        return None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Seal"})
        with urllib.request.urlopen(request, timeout=10) as response:
            data = response.read()
    except Exception:  # noqa: BLE001 - a missing thumbnail is not an error
        return None

    try:
        from PIL import Image, ImageTk  # type: ignore[import-not-found]
    except ImportError:
        ImageTk = None  # type: ignore[assignment]

    if ImageTk is not None:
        try:
            import io

            image = Image.open(io.BytesIO(data)).convert("RGBA")
            image.thumbnail((width, height))
            return ImageTk.PhotoImage(image)
        except Exception:  # noqa: BLE001 - a broken image is not an error
            return None

    try:
        image = tk.PhotoImage(data=data)
    except Exception:  # noqa: BLE001 - only png images are supported
        return None

    ratio = min(width / image.width(), height / image.height())
    if ratio < 1:
        image = image.subsample(max(1, int(1 / ratio)))
    return image


class Card(ttk.Frame):
    """A frame with a surface background and a border."""

    def __init__(self, master: tk.Misc, palette: Palette, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.configure(style="Surface.TFrame", padding=16)
        self.palette = palette
