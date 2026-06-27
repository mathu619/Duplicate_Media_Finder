import os
from pathlib import Path
from typing import Iterator

from video_app.models.scan_config import ScanConfig, ScanRoot

VIDEO_EXTENSIONS = frozenset(
    {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".mts", ".vob",
        ".3gp", ".3g2", ".ogv", ".rm", ".rmvb", ".asf", ".divx",
        ".f4v", ".mxf",
    }
)


def is_video_file(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in VIDEO_EXTENSIONS


def iter_video_files(config: ScanConfig) -> Iterator[Path]:
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
        if not p.exists() or not p.is_file() or not is_video_file(p.name):
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
                if is_video_file(name):
                    yield Path(dirpath) / name
    else:
        try:
            with os.scandir(base) as it:
                for entry in it:
                    if entry.is_file(follow_symlinks=False) and is_video_file(entry.name):
                        yield Path(entry.path)
        except OSError:
            return
