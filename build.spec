# PyInstaller spec for YT7th (Windows + macOS)
# Build with: pyinstaller build.spec
import os
import sys

from PyInstaller.utils.hooks import collect_all

sys.path.insert(0, os.path.abspath("."))
from version import __version__

block_cipher = None

datas = [("assets", "assets")]
if os.path.isdir("bin"):
    datas.append(("bin", "bin"))
binaries = []
hiddenimports = ["customtkinter"]

# Bundle data files and submodules these packages load at runtime.
for pkg in ("yt_dlp", "yt_dlp_ejs", "customtkinter"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

is_mac = sys.platform == "darwin"
icon = "assets/logo.icns" if is_mac else "assets/logo.ico"
if not os.path.exists(icon):
    icon = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YT7th",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=not is_mac,            # UPX can corrupt macOS binaries
    console=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=not is_mac,
    name="YT7th",
)

if is_mac:
    app = BUNDLE(
        coll,
        name="YT7th.app",
        icon=icon,
        bundle_identifier="com.seventh.yt7th",
        info_plist={
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
