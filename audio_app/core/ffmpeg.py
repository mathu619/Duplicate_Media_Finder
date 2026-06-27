import os
import shutil
import subprocess
import sys
from pathlib import Path

_CREATE_NO_WINDOW = 0x08000000


class FFmpegNotFound(Exception):
    pass


class ChromaprintNotFound(Exception):
    pass


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "DuplicateMediaFinder"
    return Path(__file__).resolve().parent.parent.parent


def vendor_dir(name: str) -> Path:
    d = project_root() / "vendor" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _candidate_vendor_files(tool_dir: str, executable: str) -> list[Path]:
    candidates = [project_root() / "vendor" / tool_dir / executable]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "vendor" / tool_dir / executable)

        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(Path(bundle_dir) / "vendor" / tool_dir / executable)
    return candidates


def _vendored(name: str) -> Path:
    return _candidate_vendor_files("ffmpeg", name)[0]


def find_ffmpeg() -> Path | None:
    for vendored in _candidate_vendor_files("ffmpeg", "ffmpeg.exe" if os.name == "nt" else "ffmpeg"):
        if vendored.exists():
            return vendored
    on_path = shutil.which("ffmpeg")
    return Path(on_path) if on_path else None


def find_ffprobe() -> Path | None:
    for vendored in _candidate_vendor_files("ffmpeg", "ffprobe.exe" if os.name == "nt" else "ffprobe"):
        if vendored.exists():
            return vendored
    on_path = shutil.which("ffprobe")
    return Path(on_path) if on_path else None


def find_fpcalc() -> Path | None:
    exe = "fpcalc.exe" if os.name == "nt" else "fpcalc"
    for vendored in _candidate_vendor_files("chromaprint", exe):
        if vendored.exists():
            return vendored
    on_path = shutil.which("fpcalc")
    return Path(on_path) if on_path else None


def require_fpcalc() -> Path:
    fp = find_fpcalc()
    if fp is None:
        raise ChromaprintNotFound(
            "Chromaprint's fpcalc not found.\n\n"
            "Use Tools > Manage dependencies, place fpcalc.exe in the 'vendor/chromaprint' folder, "
            "or install Chromaprint so that 'fpcalc' is on your PATH.\n\n"
            "Download from https://acoustid.org/chromaprint (pick the Windows build)."
        )
    return fp


def require_ffmpeg() -> tuple[Path, Path]:
    ff = find_ffmpeg()
    fp = find_ffprobe()
    if ff is None or fp is None:
        raise FFmpegNotFound(
            "FFmpeg and/or ffprobe not found.\n\n"
            "Use Tools > Manage dependencies, place ffmpeg.exe and ffprobe.exe in the 'vendor/ffmpeg' folder, "
            "or install FFmpeg so that 'ffmpeg' and 'ffprobe' are on your PATH.\n\n"
            "Download from https://www.gyan.dev/ffmpeg/builds/ (pick the 'release essentials' build)."
        )
    return ff, fp


def popen(cmd: list[str], **kwargs) -> subprocess.Popen:
    if os.name == "nt":
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
    return subprocess.Popen(cmd, **kwargs)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    if os.name == "nt":
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
    return subprocess.run(cmd, **kwargs)
