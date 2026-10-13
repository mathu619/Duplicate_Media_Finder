# Third-Party Notices

Mathu's Duplicate Media Finder is licensed under the GNU General Public License v3.0 (see `LICENSE`).
It uses the following third-party software, each under its own license.

## Python libraries (bundled in the release executable)

| Component | License | Source |
|---|---|---|
| Python | PSF License | https://www.python.org/ |
| PySide6 / Qt for Python | LGPL v3 | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Qt 6 | LGPL v3 | https://code.qt.io/ |
| Pillow | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |
| ImageHash | BSD 2-Clause | https://github.com/JohannesBuchner/imagehash |
| NumPy | BSD 3-Clause | https://github.com/numpy/numpy |
| Send2Trash | BSD 3-Clause | https://github.com/arsenetar/send2trash |
| PyInstaller bootloader | GPL v2 with bootloader exception | https://github.com/pyinstaller/pyinstaller |

PySide6 and Qt are used under the LGPL v3. The complete source code of this application
is available in this repository, so you can rebuild the executable against your own
modified version of PySide6 / Qt (see "Building from source" in `README.md`).

## External tools (not bundled)

These programs are **not** included in the repository or the release executable.
When they are missing, the app offers to download them from their official
distribution sites into `%LOCALAPPDATA%\DuplicateMediaFinder\vendor`, and runs them
as separate programs.

| Component | License | Source |
|---|---|---|
| FFmpeg / FFprobe (gyan.dev "release essentials" build) | GPL v3 (build configuration) | https://ffmpeg.org/ · https://www.gyan.dev/ffmpeg/builds/ |
| Chromaprint `fpcalc` 1.5.1 | MIT / LGPL v2.1 (see project) | https://github.com/acoustid/chromaprint |
