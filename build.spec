# PyInstaller spec for YT7th
# Build with: pyinstaller build.spec
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

datas = [("assets", "assets")]
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YT7th",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/logo.ico" if os.path.exists("assets/logo.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="YT7th",
)
