# YT7th - Design Spec

Date: 2026-06-28

## Purpose
Desktop YouTube downloader for personal archiving of videos and playlists. Packaged as a Windows `.exe`. Respects YouTube's rules; README states the tool is intended for personal archival use only and does not promote other usage.

## Stack
- Python 3.11+
- yt-dlp (download engine)
- customtkinter (dark modern GUI)
- SQLite (history) + JSON (settings)
- PyInstaller (.exe packaging)

## Features (v1)
- User-selectable quality/format at runtime
- Video + playlist downloads
- Audio-only extraction (MP3/M4A)
- Subtitle/caption download
- Download history log
- Local authenticated downloads via browser cookies (member-only / private)

## Architecture
| Layer | Responsibility |
|---|---|
| Downloader Engine | yt-dlp wrapper: video, playlist, audio, subs, progress hooks |
| Auth Manager | Browser cookie extraction for authenticated downloads |
| Data Manager | settings.json + history.db (SQLite) |
| UI Layer | customtkinter app: Home, History, Settings views |

## File Structure
```
YT7th/
- main.py
- downloader.py
- auth.py
- data.py
- ui/
  - app.py
  - home.py
  - history.py
  - settings.py
- assets/logo.svg
- requirements.txt
- build.spec
```

## UI
- Left sidebar: icon + small label per tab (Home / History / Settings)
- Active tab highlighted with dark red accent (#8B0000)
- Logo top-left of sidebar
- Home: URL input + Download button, quality/format dropdowns, audio-only and subtitle checkboxes, progress bar with percent/speed/title
- Dark modern aesthetic

## Conventions
- No em dashes anywhere in code, comments, or docs. Use regular dashes.
