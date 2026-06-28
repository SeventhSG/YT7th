<div align="center">

<img src="assets/logo.png" width="96" alt="YT7th logo">

# YT7th

**A clean, dark-themed desktop app for archiving your own YouTube videos and playlists.**

Built with Python, yt-dlp, and customtkinter.

</div>

---

## Intended use

YT7th is for **personal archival only** - saving videos for your own offline use. It is **not** intended or promoted for redistribution, piracy, or any use that violates YouTube's Terms of Service. Please respect YouTube's rules and the rights of content creators. You are responsible for how you use this tool.

## Features

- Pick quality and format at download time (up to 4K / best available)
- Single videos and full playlists
- Audio-only extraction (MP3 / M4A)
- Subtitle / caption download
- Download history log with quick "open folder"
- Cancel a download mid-flight
- Smart authentication: public videos download with no login data sent; cookies are only used when a video is gated (member-only, private, age-restricted)
- Friendly, plain-language error messages
- Dark modern UI with a left sidebar

## Requirements

- **Python 3.11+**
- **[FFmpeg](https://ffmpeg.org/)** on your PATH - merges video/audio and extracts audio
- **A JavaScript runtime** on your PATH - **[Node.js](https://nodejs.org/) 22+** (recommended), [Deno](https://deno.com/), or Bun. YouTube requires solving a JavaScript challenge to release video streams; without a runtime, only image storyboards are available and downloads fail with "Requested format is not available". The EJS solver scripts ship with `yt-dlp[default]` (already in `requirements.txt`).

## Install and run

```bash
pip install -r requirements.txt
python main.py
```

## Build a standalone .exe

```bash
pip install pyinstaller
pyinstaller build.spec
```

The packaged app appears in `dist/YT7th/`. Note: the `.exe` still relies on FFmpeg and a JS runtime being installed on the target machine.

## Authentication (member-only / private videos)

To archive content you have access to, give YT7th your login cookies. Everything stays local; nothing is uploaded anywhere. YT7th only uses these when a video actually requires them.

Open **Settings** and choose one of:

1. **Cookies file (recommended).** Export a `cookies.txt` with a browser extension such as "Get cookies.txt LOCALLY", then select it. Works even while the browser is open and is immune to Chromium app-bound cookie encryption.
2. **Read from browser.** Pick the browser you are logged into. On Windows you must close the browser completely first (it locks its cookie database while running), and on Chrome/Brave v127+ this can fail due to app-bound encryption - so the cookies file method is more reliable.

## Project layout

```
YT7th/
  main.py            entry point
  downloader.py      yt-dlp engine, JS runtime detection, smart auth, errors
  auth.py            cookie handling (file + browser)
  data.py            settings (JSON) + history (SQLite)
  list_formats.py    diagnostic: list formats yt-dlp sees for a URL
  ui/
    app.py           main window + sidebar
    theme.py         design tokens
    home.py          download view
    history.py       history view
    settings.py      settings view
    messages.py      playful in-app copy
  assets/            logo (svg, png, ico)
  build.spec         PyInstaller config
```

## Credits

Developed by [SeventhSG](https://github.com/SeventhSG).

Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [customtkinter](https://github.com/TomSchimansky/CustomTkinter).

## License

MIT. See [LICENSE](LICENSE).
