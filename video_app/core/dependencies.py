import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from video_app.core.ffmpeg import (
    find_ffmpeg,
    find_ffprobe,
    find_fpcalc,
    project_root,
    vendor_dir,
)

# Stable URLs (gyan.dev provides a redirect-stable "release essentials" URL;
# Chromaprint v1.5.1 has been the latest stable release since 2021).
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
CHROMAPRINT_URL = (
    "https://github.com/acoustid/chromaprint/releases/download/"
    "v1.5.1/chromaprint-fpcalc-1.5.1-windows-x86_64.zip"
)

# Reported as (bytes_downloaded, bytes_total_or_zero, status_text)
ProgressCallback = Callable[[int, int, str], None]


class DependencyDownloadError(Exception):
    pass


def status() -> dict[str, bool]:
    return {
        "ffmpeg": find_ffmpeg() is not None,
        "ffprobe": find_ffprobe() is not None,
        "fpcalc": find_fpcalc() is not None,
    }


def _download_to_path(url: str, dest: Path, on_progress: ProgressCallback) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "DuplicateVideoFinder/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
            total = int(resp.getheader("Content-Length") or 0)
            done = 0
            on_progress(0, total, "Downloading…")
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total:
                    msg = f"Downloading… {done / 1_000_000:.1f} / {total / 1_000_000:.1f} MB"
                else:
                    msg = f"Downloading… {done / 1_000_000:.1f} MB"
                on_progress(done, total, msg)
    except urllib.error.URLError as e:
        raise DependencyDownloadError(f"Network error: {e.reason}") from e
    except OSError as e:
        raise DependencyDownloadError(f"Disk error: {e}") from e


def _extract_named_files(zip_path: Path, target_dir: Path, wanted_lower: set[str]) -> set[str]:
    """Extract files whose basename (lowercased) is in wanted_lower into target_dir.
    Returns the set of basenames actually extracted."""
    extracted: set[str] = set()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            base = Path(info.filename).name.lower()
            if base in wanted_lower and base not in extracted:
                with z.open(info) as src, open(target_dir / base, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.add(base)
    return extracted


def install_ffmpeg(on_progress: ProgressCallback) -> None:
    target = vendor_dir("ffmpeg")
    tmp_zip = project_root() / "vendor" / "_ffmpeg_tmp.zip"
    try:
        on_progress(0, 0, "Connecting to FFmpeg server…")
        _download_to_path(FFMPEG_URL, tmp_zip, on_progress)
        on_progress(0, 0, "Extracting FFmpeg…")
        wanted = {"ffmpeg.exe", "ffprobe.exe"}
        got = _extract_named_files(tmp_zip, target, wanted)
        missing = wanted - got
        if missing:
            raise DependencyDownloadError(
                f"Downloaded archive did not contain: {', '.join(sorted(missing))}"
            )
    finally:
        try:
            tmp_zip.unlink(missing_ok=True)
        except OSError:
            pass


def install_chromaprint(on_progress: ProgressCallback) -> None:
    target = vendor_dir("chromaprint")
    tmp_zip = project_root() / "vendor" / "_chromaprint_tmp.zip"
    try:
        on_progress(0, 0, "Connecting to Chromaprint server…")
        _download_to_path(CHROMAPRINT_URL, tmp_zip, on_progress)
        on_progress(0, 0, "Extracting Chromaprint…")
        got = _extract_named_files(tmp_zip, target, {"fpcalc.exe"})
        if "fpcalc.exe" not in got:
            raise DependencyDownloadError("Downloaded archive did not contain fpcalc.exe")
    finally:
        try:
            tmp_zip.unlink(missing_ok=True)
        except OSError:
            pass
