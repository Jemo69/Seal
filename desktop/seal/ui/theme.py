"""The colors and the fonts of the application."""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk


@dataclass(frozen=True)
class Palette:
    """Every color the application uses."""

    background: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_text: str
    success: str
    error: str
    selection: str


LIGHT = Palette(
    background="#f6f7f9",
    surface="#ffffff",
    surface_alt="#eef0f4",
    border="#d8dce3",
    text="#1b1f27",
    text_muted="#666e7d",
    accent="#f8e444",
    accent_text="#1b1f27",
    success="#2e9e5b",
    error="#d9534f",
    selection="#dbe6ff",
)

DARK = Palette(
    background="#14161a",
    surface="#1c1f25",
    surface_alt="#23272f",
    border="#333945",
    text="#e8eaee",
    text_muted="#9aa2b1",
    accent="#f8e444",
    accent_text="#14161a",
    success="#3fbf74",
    error="#ef6b66",
    selection="#2b3a55",
)


def ui_font() -> str:
    """The font family of the current platform."""
    if sys.platform == "win32":
        return "Segoe UI"
    if sys.platform == "darwin":
        return "Helvetica Neue"
    return "DejaVu Sans"


def apply_theme(root: tk.Misc, palette: Palette) -> None:
    """Applies the palette to the ttk styles of the application."""
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(background=palette.background)

    style.configure(".", background=palette.background, foreground=palette.text,
                     fieldbackground=palette.surface, bordercolor=palette.border,
                     lightcolor=palette.surface, darkcolor=palette.background,
                     font=(ui_font(), 10))
    style.configure("TFrame", background=palette.background)
    style.configure("Surface.TFrame", background=palette.surface)
    style.configure("TLabel", background=palette.background, foreground=palette.text)
    style.configure("Muted.TLabel", background=palette.background, foreground=palette.text_muted)
    style.configure("Surface.TLabel", background=palette.surface, foreground=palette.text)
    style.configure("Title.TLabel", font=(ui_font(), 16, "bold"))
    style.configure("Subtitle.TLabel", font=(ui_font(), 10, "bold"))
    style.configure("TButton", background=palette.surface_alt, foreground=palette.text,
                    bordercolor=palette.border, focuscolor=palette.accent, padding=(12, 7))
    style.map("TButton",
              background=[("active", palette.border), ("disabled", palette.surface_alt)],
              foreground=[("disabled", palette.text_muted)])
    style.configure("Accent.TButton", background=palette.accent, foreground=palette.accent_text,
                    bordercolor=palette.accent, padding=(16, 8), font=(ui_font(), 10, "bold"))
    style.map("Accent.TButton",
              background=[("active", palette.accent), ("disabled", palette.surface_alt)],
              foreground=[("disabled", palette.text_muted)])
    style.configure("Danger.TButton", background=palette.surface_alt, foreground=palette.error)
    style.configure("TEntry", fieldbackground=palette.surface, foreground=palette.text,
                    bordercolor=palette.border, insertcolor=palette.text, padding=(8, 6))
    style.configure("TCombobox", fieldbackground=palette.surface, background=palette.surface,
                    foreground=palette.text, bordercolor=palette.border, arrowcolor=palette.text)
    style.map("TCombobox", fieldbackground=[("readonly", palette.surface)])
    style.configure("TCheckbutton", background=palette.background, foreground=palette.text)
    style.configure("Surface.TCheckbutton", background=palette.surface, foreground=palette.text)
    style.configure("TNotebook", background=palette.background, bordercolor=palette.border)
    style.configure("TNotebook.Tab", background=palette.surface_alt, foreground=palette.text_muted,
                    padding=(18, 9), bordercolor=palette.border)
    style.map("TNotebook.Tab",
              background=[("selected", palette.surface)],
              foreground=[("selected", palette.text)])
    style.configure("Treeview", background=palette.surface, fieldbackground=palette.surface,
                    foreground=palette.text, bordercolor=palette.border, rowheight=28)
    style.configure("Treeview.Heading", background=palette.surface_alt, foreground=palette.text,
                    font=(ui_font(), 10, "bold"), bordercolor=palette.border)
    style.map("Treeview", background=[("selected", palette.selection)])
    style.configure("Horizontal.TProgressbar", background=palette.accent,
                    troughcolor=palette.surface_alt, bordercolor=palette.border)
    style.configure("Vertical.TScrollbar", background=palette.surface_alt,
                    troughcolor=palette.background, bordercolor=palette.border)
    style.configure("TSeparator", background=palette.border)
