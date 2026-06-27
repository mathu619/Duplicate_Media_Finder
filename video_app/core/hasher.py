import hashlib
from pathlib import Path

_QUICK_SAMPLE_BYTES = 64 * 1024
_FULL_CHUNK_BYTES = 1024 * 1024


def quick_hash(path: Path, size: int) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        if size <= _QUICK_SAMPLE_BYTES * 2:
            h.update(f.read())
        else:
            h.update(f.read(_QUICK_SAMPLE_BYTES))
            f.seek(-_QUICK_SAMPLE_BYTES, 2)
            h.update(f.read(_QUICK_SAMPLE_BYTES))
    return h.hexdigest()


def full_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_FULL_CHUNK_BYTES), b""):
            h.update(chunk)
    return h.hexdigest()
