"""YT7th - personal YouTube archiver. Entry point.

Default: launch the desktop UI.
`--serve`: run headless as the local engine daemon (used by editor-host
plugins and auto-launched on demand). Avoids importing the UI toolkit.
"""
import sys

from yt7th_engine import resources


def main():
    resources.bootstrap()
    if "--serve" in sys.argv:
        from yt7th_engine.service import run_server
        run_server()
    else:
        from ui.app import run
        run()


if __name__ == "__main__":
    main()
