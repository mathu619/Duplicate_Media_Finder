# Mathu's Duplicate Media Finder

**Find and remove duplicate videos and songs on Windows, including copies that are not byte-for-byte identical.**

Most duplicate finders only catch exact copies. This one also finds the same video or song
after it has been re-encoded, resized, converted to another format, renamed, or trimmed.
It then suggests which copy to keep and sends the rest to the Recycle Bin.

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue)
![Python](https://img.shields.io/badge/python-3.13-blue)
![License](https://img.shields.io/badge/license-GPLv3-green)

<!-- TODO: screenshots
![Mode selection](docs/screenshots/selection.png)
![Video results](docs/screenshots/video-results.png)
-->

---

## Contents

- [Features](#features)
- [Download and install](#download-and-install)
- [How to use](#how-to-use)
- [Detection modes](#detection-modes)
- [How it works](#how-it-works)
- [Supported file types](#supported-file-types)
- [Privacy and safety](#privacy-and-safety)
- [Where files are stored](#where-files-are-stored)
- [Running from source](#running-from-source)
- [Building the executable](#building-the-executable)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Videos and music in one app.** Choose *Video Files* or *Audio Files* on the start screen.
- **Finds near-duplicates, not just exact copies.** The same content still matches when the
  format, resolution, bitrate, file name or folder is different.
- **Finds trimmed copies and clips.** Spots a video with the intro cut off, or a song excerpt
  that is part of a longer recording.
- **Picks the best copy for you.** In every duplicate group the highest-quality file is kept
  and the others are marked for removal. You can change the selection before deleting.
- **Safe by design.** Nothing is ever deleted permanently. Files go to the Windows Recycle Bin,
  so you can restore anything.
- **Shows how much space you'll save** before you delete anything.
- **Fast repeat scans.** File fingerprints are cached, so scanning the same folders again only
  processes new or changed files.
- **Flexible scan targets.** Add whole folders (with or without subfolders) and individual files.
- **Extra tool for videos:** find video files that have **no audio track**.
- **Modern dark interface** with the Windows 11 translucent (acrylic) look.

---

## Download and install

1. Go to the [Releases](../../releases) page.
2. Download `DuplicateMediaFinder-onefile.exe`.
3. Run it. No installation is needed.

> Windows SmartScreen may warn about an unrecognised app because the executable is not
> code-signed. Click **More info → Run anyway**. If you'd rather not, you can
> [run it from source](#running-from-source) instead.

### First run: helper tools

The app relies on two free, open-source command-line tools:

| Tool | Used for |
|---|---|
| [FFmpeg / FFprobe](https://ffmpeg.org/) | Reading media details and extracting video frames |
| [Chromaprint `fpcalc`](https://acoustid.org/chromaprint) | Creating audio fingerprints |

If they are missing, the app offers to download them from their official sites
(about 100 MB in total). This only happens once. You can also open
**Tools → Manage dependencies…** at any time.

If FFmpeg and `fpcalc` are already installed and on your `PATH`, the app uses those instead.

---

## How to use

1. **Pick a media type** on the start screen: *Video Files* or *Audio Files*.
2. **Add what to scan**:
   - **+ Add Folder** adds a folder. Tick **Exclude Subfolders** to scan only the top level.
   - **+ Add Files** adds individual files.
   - **Remove** takes the selected entry off the list.
3. **Choose a detection mode** (see [below](#detection-modes)). Start with the default; use a
   deeper mode when you want to catch edited or re-encoded copies.
4. Click **Start Scan**. You can cancel at any time.
5. **Review the results.** Files are shown in groups of duplicates, with the total space you
   could free. In each group:
   - the best-quality copy is left **unmarked** (kept),
   - the other copies are **marked** for removal,
   - for a *contained clip* group, the shorter clip is marked and the full-length file is kept.

   Right-click any file to **play it in your default player** or **show it in its folder**.
   Use the buttons at the top to **Keep best quality per group**, **Mark every file** or
   **Unmark all**.
6. Click **Send checked to Recycle Bin** to remove the marked files.

---

## Detection modes

Faster modes find fewer kinds of duplicates. Deeper modes take longer but find more.

### Video

| Mode | Finds | Speed |
|---|---|---|
| **Basic** | Exact copies (identical files, even with different names) | Seconds |
| **Advanced** | Videos that *look* the same: re-encoded, resized or converted copies | Minutes |
| **Deep (Fast)** | Videos whose *audio track* is the same | Minutes |
| **Deep (Slow)** | Same content even when one copy is trimmed at the start or end, plus clips contained in longer videos | Longest |

### Audio

| Mode | Finds | Speed |
|---|---|---|
| **Basic** | Exact copies (identical files) | Seconds |
| **Deep (Fast)** | Songs that *sound* the same: different format, bitrate or tags | Minutes |
| **Contained Clips** | Short excerpts that appear inside longer recordings | Longer |

---

## How it works

**Exact copies (Basic).** Files are first grouped by size. Files with the same size are compared
using a quick SHA-256 hash of their first and last bytes, then confirmed with a full SHA-256
hash. Only truly identical files are reported.

**Visual matching (Video → Advanced).** FFmpeg samples up to about 150 frames evenly across
each video and shrinks them to tiny thumbnails. Each frame gets a *perceptual hash*, a short
"visual signature" that stays almost the same after re-encoding or resizing. Videos with similar
lengths are compared frame by frame, and pairs whose signatures are close enough are reported.

**Audio fingerprinting (Video → Deep Fast, Audio → Deep Fast).** Chromaprint, the same
technology behind the AcoustID music-recognition service, produces a fingerprint of the sound.
Two files whose fingerprints are at least 92% similar, and whose lengths are close, count as
duplicates.

**Timeline matching (Video → Deep Slow, Audio → Contained Clips).** Fingerprints are taken at a
fixed rate (for video, one frame per second) so the timelines of two files can be lined up. The
app slides the shorter file along the longer one to find the best alignment. This is how it
detects copies with the start trimmed off, and clips that appear inside a longer file.

**Choosing the keeper.** Within a group, files are ranked by:
- video: resolution → bitrate → duration → file size
- audio: bitrate → duration → file size

The highest-ranked file is kept.

---

## Supported file types

**Video:** `.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpg` `.mpeg` `.ts`
`.m2ts` `.mts` `.vob` `.3gp` `.3g2` `.ogv` `.rm` `.rmvb` `.asf` `.divx` `.f4v` `.mxf`

**Audio:** `.mp3` `.flac` `.wav` `.m4a` `.aac` `.ogg` `.oga` `.opus` `.wma` `.aiff` `.aif`
`.alac` `.ape` `.m4b` `.mp2` `.amr` `.ac3` `.dts` `.mid` `.midi`

---

## Privacy and safety

- **Everything runs on your computer.** Your files are never uploaded anywhere.
- **No accounts, tracking or analytics.** The only internet access is the optional one-time
  download of FFmpeg and Chromaprint from their official sites.
- **No permanent deletion.** Removed files go to the Recycle Bin.
- **Nothing is removed without your say.** The app only suggests; you confirm what gets deleted.

---

## Where files are stored

| What | Location |
|---|---|
| Downloaded FFmpeg / `fpcalc` | `%LOCALAPPDATA%\DuplicateMediaFinder\vendor\` |
| Video fingerprint cache | `%LOCALAPPDATA%\DuplicateVideoFinder\cache.sqlite` |
| Audio fingerprint cache | `%LOCALAPPDATA%\DuplicateAudioFinder\cache.sqlite` |

Deleting a cache file is safe. The app rebuilds it on the next scan (which will be slower).

To uninstall, delete the `.exe` and the folders above.

---

## Running from source

Requirements: **Windows 10 or 11** and **Python 3.13**.

```powershell
git clone https://github.com/mathu619/Duplicate_Media_Finder.git
cd Duplicate_Media_Finder
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

When running from source, you can put the helper tools in the project's `vendor` folder
instead of downloading them through the app:

```
vendor/ffmpeg/ffmpeg.exe
vendor/ffmpeg/ffprobe.exe
vendor/chromaprint/fpcalc.exe
```

Optional: for the intended typography, place the **Inter** font files in `resources/`
(see [resources/README.md](resources/README.md)). Without them the app uses the system font.

---

## Building the executable

```powershell
pip install -r requirements-dev.txt
pyinstaller DuplicateMediaFinderOneFile.spec
```

The single-file executable is written to `dist\DuplicateMediaFinder-onefile.exe`.

To build a folder version instead (starts faster), use `pyinstaller DuplicateMediaFinder.spec`;
the output goes to `dist\DuplicateMediaFinder\`.

The app icon is generated from the in-app logo with `python tools/generate_icon.py`.

---

## Project structure

```
main.py                 Entry point: opens the start screen
media_finder/           Start screen where you pick Video or Audio
video_app/              Duplicate video finder
  core/                 Scanning, hashing, fingerprinting, matching, caching, deleting
    fingerprint/        Frame hashes (tier 2), audio & timeline fingerprints (tier 3)
  models/               Data classes: files, metadata, duplicate groups, scan settings
  ui/                   Windows, dialogs, theme (Qt / PySide6)
  workers/              Background threads for scans and downloads
audio_app/              Duplicate audio finder (same layout as video_app)
resources/              App icon and optional fonts
tools/                  Helper scripts (icon generator)
vendor/                 Optional local FFmpeg / fpcalc for running from source
```

Built with [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python),
[ImageHash](https://github.com/JohannesBuchner/imagehash), [Pillow](https://python-pillow.org/),
[NumPy](https://numpy.org/) and [Send2Trash](https://github.com/arsenetar/send2trash).

---

## Troubleshooting

**The app says FFmpeg or fpcalc is missing.**
Use **Tools → Manage dependencies…** to download them. If the download fails (for example,
behind a firewall), download them manually from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
("release essentials") and [Chromaprint](https://acoustid.org/chromaprint) and place them in
`%LOCALAPPDATA%\DuplicateMediaFinder\vendor\ffmpeg\` and `...\vendor\chromaprint\`.

**A scan is slow.**
The first deep scan has to fingerprint every file. Later scans reuse the cache and are much
faster. Try **Advanced** (video) or **Deep (Fast)** before **Deep (Slow)**.

**Two files I know are duplicates weren't matched.**
Try a deeper mode. **Advanced** only compares videos with similar lengths; **Deep (Slow)**
handles trimmed copies. Videos without an audio track can't be matched by **Deep (Fast)**.

**I deleted the wrong file.**
Open the Windows Recycle Bin and restore it.

**Windows SmartScreen blocks the exe.**
The executable isn't code-signed. Click **More info → Run anyway**, or run from source.

---

## Contributing

Bug reports, ideas and pull requests are welcome.

- **Found a bug?** [Open an issue](../../issues) with your Windows version, the detection mode
  you used and what happened.
- **Want to change code?** Fork the repo, create a branch, and open a pull request describing
  the change and how you tested it.

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE). You may use,
study, share and modify it. If you distribute a modified version, it must also be released
under the GPLv3 with its source code.

Third-party components and their licenses are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). FFmpeg and Chromaprint are not included in
this repository; they are downloaded separately from their official sources.
