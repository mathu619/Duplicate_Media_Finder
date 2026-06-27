import os
from pathlib import Path
from typing import Iterator

from audio_app.models.scan_config import ScanConfig, ScanRoot

AUDIO_EXTENSIONS = frozenset(
    {
        ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".oga",
        ".opus", ".wma", ".aiff", ".aif", ".alac", ".ape", ".m4b",
        ".mp2", ".amr", ".ac3", ".dts", ".mid", ".midi",
    }
)


def is_audio_file(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in AUDIO_EXTENSIONS


def iter_audio_files(config: ScanConfig) -> Iterator[Path]:
    seen: set[str] = set()
    for root in config.roots:
        for p in _walk_root(root):
            key = str(p).lower()
            if key in seen:
                continue
            seen.add(key)
            yield p
    for raw in config.extra_files:
        p = Path(raw)
        if not p.exists() or not p.is_file() or not is_audio_file(p.name):
            continue
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        yield p


def _walk_root(root: ScanRoot) -> Iterator[Path]:
    base = Path(root.path)
    if not base.exists():
        return
    if root.recursive:
        for dirpath, _dirnames, filenames in os.walk(base, followlinks=False):
            for name in filenames:
                if is_audio_file(name):
                    yield Path(dirpath) / name
    else:
        try:
            with os.scandir(base) as it:
                for entry in it:
                    if entry.is_file(follow_symlinks=False) and is_audio_file(entry.name):
                        yield Path(entry.path)
        except OSError:
            return
