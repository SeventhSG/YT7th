"""YT7th panel for DaVinci Resolve.

Install: copy the repository's `hosts/` tree (or at least hosts/common and
hosts/resolve) somewhere on disk, then place/symlink this file under Resolve's
scripts folder, e.g.:
    .../Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
Run it from Resolve's  Workspace > Scripts  menu.

This is the only Resolve-specific layer and cannot run outside Resolve, so it
stays thin: the engine client and the import logic are tested separately.
"""
import sys
import threading
from pathlib import Path

# Make the sibling `hosts` package importable regardless of where Resolve
# launches us from (…/hosts/resolve/YT7th.py -> add the dir containing hosts/).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from hosts.common.engine_client import connect, EngineError  # noqa: E402
from hosts.common.job_runner import run_job  # noqa: E402
from hosts.resolve.resolve_host import ResolveHost  # noqa: E402

QUALITIES = ["Best", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
VIDEO_FORMATS = ["MP4", "MKV", "WEBM"]
AUDIO_FORMATS = ["MP3", "M4A"]
POLL_SECONDS = 1.0

# --- Resolve globals ------------------------------------------------------
# When launched from Resolve's Scripts menu, `resolve`, `fusion`/`fu` and
# `bmd` are injected. Guard so the file at least imports elsewhere.
try:
    resolve  # type: ignore  # noqa: F821
except NameError:  # pragma: no cover - only hit outside Resolve
    try:
        import DaVinciResolveScript as bmd  # type: ignore
        resolve = bmd.scriptapp("Resolve")  # type: ignore
    except Exception:  # noqa: BLE001
        resolve = None  # type: ignore

try:
    fusion  # type: ignore  # noqa: F821
except NameError:  # pragma: no cover
    fusion = resolve.Fusion() if resolve else None  # type: ignore

try:
    bmd  # type: ignore  # noqa: F821
except NameError:  # pragma: no cover
    try:
        import BlackmagicFusion as bmd  # type: ignore
    except Exception:  # noqa: BLE001
        bmd = None  # type: ignore


def build_ui():  # pragma: no cover - requires Resolve's UI runtime
    ui = fusion.UIManager
    disp = bmd.UIDispatcher(ui)

    win = disp.AddWindow(
        {"ID": "YT7th", "WindowTitle": "YT7th - Download to Timeline",
         "Geometry": [200, 200, 560, 360]},
        [
            ui.VGroup([
                ui.Label({"Text": "YouTube URL", "Weight": 0}),
                ui.LineEdit({"ID": "Url", "PlaceholderText":
                             "https://youtube.com/watch?v=..."}),
                ui.HGroup({"Weight": 0}, [
                    ui.VGroup([ui.Label({"Text": "Quality"}),
                               ui.ComboBox({"ID": "Quality"})]),
                    ui.VGroup([ui.Label({"Text": "Format"}),
                               ui.ComboBox({"ID": "Format"})]),
                ]),
                ui.CheckBox({"ID": "AudioOnly", "Text": "Audio only"}),
                ui.CheckBox({"ID": "Append", "Text":
                             "Append to current timeline", "Checked": True}),
                ui.Button({"ID": "Download", "Text": "Download"}),
                ui.Label({"ID": "Status", "Text": "Ready.",
                          "WordWrap": True}),
            ]),
        ])

    items = win.GetItems()
    for q in QUALITIES:
        items["Quality"].AddItem(q)
    items["Quality"].CurrentText = "1080p"
    for f in VIDEO_FORMATS:
        items["Format"].AddItem(f)

    def status(text):
        items["Status"].Text = text

    def on_audio_toggle(ev):
        items["Format"].Clear()
        for f in (AUDIO_FORMATS if items["AudioOnly"].Checked else VIDEO_FORMATS):
            items["Format"].AddItem(f)

    def worker(client, url, settings, append):
        outcome = run_job(client, ResolveHost(resolve), url, settings,
                          append_to_timeline=append, on_status=status,
                          poll_interval=POLL_SECONDS)
        status(outcome.message)

    def on_download(ev):
        url = items["Url"].Text.strip()
        if not url:
            status("Paste a URL first.")
            return
        settings = {
            "quality": items["Quality"].CurrentText,
            "format": items["Format"].CurrentText,
            "audio_only": bool(items["AudioOnly"].Checked),
        }
        append = bool(items["Append"].Checked)
        status("Starting engine...")
        try:
            client = connect()
        except EngineError as e:
            status(f"Error: {e}")
            return
        items["Url"].Text = ""
        threading.Thread(target=worker,
                         args=(client, url, settings, append),
                         daemon=True).start()

    # Attribute form is the documented way to bind handlers by widget ID.
    win.On.AudioOnly.Clicked = on_audio_toggle
    win.On.Download.Clicked = on_download
    win.On.YT7th.Close = lambda ev: disp.ExitLoop()

    win.Show()
    disp.RunLoop()
    win.Hide()


if __name__ == "__main__":
    if resolve is None or fusion is None:
        print("This script must be run from inside DaVinci Resolve.")
    else:
        build_ui()
