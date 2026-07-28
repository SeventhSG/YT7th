# YT7th - Premiere Pro panel

A CEP panel that downloads a YouTube URL and imports the clip into the current
Premiere project, optionally appending it to the active sequence.

## How it works

```
panel UI (index.html/main.js)          host (index.jsx / ExtendScript)
        |                                        ^
        | engine.js (Node: find/launch engine)   | evalScript(yt7thImport)
        v                                        |
  YT7th engine daemon  --HTTP 127.0.0.1-->  downloads the file
```

`engine.js` is plain Node and unit-tested (`engine.test.js`). `main.js` and
`index.jsx` are the Premiere-only glue that can only run inside the app.

## Install (release build)

The release zip `YT7th-Premiere-<os>.zip` unzips to a
`com.seventh.yt7th.premiere/` folder that already contains the engine under
`engine/`. Copy it into the CEP extensions folder:

- Windows: `%APPDATA%\Adobe\CEP\extensions\`
- macOS: `~/Library/Application Support/Adobe/CEP/extensions/`

Then in Premiere: **Window > Extensions > YT7th**.

## Install (from source, for development)

1. Copy (or symlink) `hosts/premiere` into the CEP extensions folder as
   `com.seventh.yt7th.premiere`.
2. Put the engine binary at `com.seventh.yt7th.premiere/engine/YT7th[.exe|.app]`,
   or set the `YT7TH_ENGINE_CMD` environment variable to the engine command
   (e.g. `python -m yt7th_engine.server`, run from the repo root).
3. Enable unsigned extensions (PlayerDebugMode):
   - Windows: `reg add HKCU\Software\Adobe\CSXS.9 /v PlayerDebugMode /t REG_SZ /d 1`
   - macOS: `defaults write com.adobe.CSXS.9 PlayerDebugMode 1`
4. Restart Premiere and open **Window > Extensions > YT7th**.

## Test the Node client

```bash
node --test hosts/premiere/client/engine.test.js
```
