# -*- mode: python ; coding: utf-8 -*-
"""Builds Seal into a single windows executable.

    pyinstaller Seal.spec

The result is written to dist/Seal.exe.
"""

from PyInstaller.utils.hooks import collect_all

# yt-dlp and instaloader ship a lot of python files, they all have to be bundled.
datas, binaries, hiddenimports = collect_all("yt_dlp")

try:
    insta_datas, insta_binaries, insta_hidden = collect_all("instaloader")
except Exception:  # instaloader is optional, the application reports it at runtime
    insta_datas, insta_binaries, insta_hidden = [], [], []

a = Analysis(
    ["seal/__main__.py"],
    pathex=[SPECPATH],
    binaries=binaries + insta_binaries,
    datas=datas + insta_datas,
    hiddenimports=hiddenimports + insta_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "test"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Seal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
