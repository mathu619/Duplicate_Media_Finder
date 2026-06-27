# Vendor binaries

Optional binaries can live here while running from source:

- `vendor/ffmpeg/ffmpeg.exe`
- `vendor/ffmpeg/ffprobe.exe`
- `vendor/chromaprint/fpcalc.exe`

Frozen executable builds install downloaded dependencies to:

`%LOCALAPPDATA%\DuplicateMediaFinder\vendor`

The app can also use these tools from `PATH` or from a `vendor` folder next to the executable.
