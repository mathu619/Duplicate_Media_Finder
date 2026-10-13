# Mathu's Duplicate Media Finder

A Windows desktop app that finds duplicate **video** and **audio** files, including
re-encoded copies, different resolutions and trimmed clips, and helps you clean them up.

<!-- TODO: Buy Me a Coffee link -->

## Features

- **Video and audio in one app.** Pick *Video Files* or *Audio Files* on the opening screen.
- **More than exact copies.** Detects files that look or sound the same even when the
  format, resolution, bitrate or file name differ.
- **Finds trimmed copies.** Deep scans can spot a clip that is part of a longer file.
- **Suggests which copy to keep.** In each group the best-quality file (resolution,
  bitrate, length, size) is marked as the keeper.
- **Safe deletes.** Removed files go to the Windows Recycle Bin, so you can restore them.
- **Fast re-scans.** Fingerprints are cached, so scanning the same folders again is quick.

### Detection modes

| Video | What it does |
|---|---|
| Basic | Exact file matches (seconds) |
| Advanced | Compares frames sampled from each video (minutes) |
| Deep (Fast) | Compares the audio track's fingerprint |
| Deep (Slow) | Full video match that handles edits and trimmed copies |

| Audio | What it does |
|---|---|
| Basic | Exact file matches |
| Deep (Fast) | Compares audio fingerprints, so re-encoded songs match |
| Contained Clips | Finds excerpts that appear inside longer files |

## Download

Get the latest `DuplicateMediaFinder-onefile.exe` from the
[Releases](../../releases) page and run it. No installation needed.

On first use, the app asks to download two free tools it relies on:
[FFmpeg](https://ffmpeg.org/) and [Chromaprint](https://acoustid.org/chromaprint) (`fpcalc`).
They are saved to `%LOCALAPPDATA%\DuplicateMediaFinder\vendor`. If you already
have them on your `PATH`, those are used instead.

## Running from source

Requires Windows and Python 3.13.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

When running from source, you can also place the tools in the project's `vendor` folder
(see [vendor/README.md](vendor/README.md)).

## Building from source

```powershell
pip install -r requirements-dev.txt
pyinstaller DuplicateMediaFinderOneFile.spec
```

The executable is written to `dist\DuplicateMediaFinder-onefile.exe`.
`DuplicateMediaFinder.spec` builds a folder version instead (`dist\DuplicateMediaFinder\`).

## License

Licensed under the [GNU General Public License v3.0](LICENSE).
Third-party components and their licenses are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
