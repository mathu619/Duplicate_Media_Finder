import struct
from pathlib import Path

from audio_app.core.ffmpeg import run

_TIMEOUT_SECONDS = 180
_MIN_SAMPLES_FOR_COMPARE = 40  # ~5 seconds at Chromaprint's 7.8 Hz sample rate


def extract_audio_fingerprint(path: Path, fpcalc_path: Path) -> tuple[float, list[int]] | None:
    """Return (duration_seconds, list-of-32-bit-ints) or None if extraction fails."""
    cmd = [str(fpcalc_path), "-raw", "-length", "0", str(path)]
    try:
        result = run(cmd, capture_output=True, timeout=_TIMEOUT_SECONDS)
    except Exception:  # noqa: BLE001
        return None
    if result.returncode != 0 or not result.stdout:
        return None

    duration: float | None = None
    fingerprint: list[int] | None = None
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        if line.startswith("DURATION="):
            try:
                duration = float(line[len("DURATION="):])
            except ValueError:
                pass
        elif line.startswith("FINGERPRINT="):
            payload = line[len("FINGERPRINT="):]
            try:
                fingerprint = [int(x) for x in payload.split(",") if x.strip()]
            except ValueError:
                fingerprint = None
    if duration is None or fingerprint is None or not fingerprint:
        return None
    return (duration, fingerprint)


def serialize(fingerprint: list[int]) -> bytes:
    return b"".join(struct.pack("<I", x & 0xFFFFFFFF) for x in fingerprint)


def deserialize(blob: bytes) -> list[int]:
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}I", blob[: n * 4]))


def audio_similarity(a: list[int], b: list[int]) -> float:
    """Fixed-alignment similarity in [0, 1]. 1.0 = identical."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n < _MIN_SAMPLES_FOR_COMPARE:
        return 0.0
    total_bits = 0
    for i in range(n):
        total_bits += ((a[i] ^ b[i]) & 0xFFFFFFFF).bit_count()
    max_bits = n * 32
    return 1.0 - (total_bits / max_bits)


def best_contained_similarity(short: list[int], long: list[int]) -> tuple[int, float]:
    """Return (best_offset, similarity) for a short fingerprint inside a long one."""
    if len(short) > len(long):
        short, long = long, short
    n = len(short)
    if n < _MIN_SAMPLES_FOR_COMPARE:
        return (0, 0.0)

    best_offset = 0
    best_similarity = 0.0
    for offset in range(len(long) - n + 1):
        total_bits = 0
        for i, value in enumerate(short):
            total_bits += ((value ^ long[offset + i]) & 0xFFFFFFFF).bit_count()
        similarity = 1.0 - (total_bits / (n * 32))
        if similarity > best_similarity:
            best_offset = offset
            best_similarity = similarity
    return (best_offset, best_similarity)
