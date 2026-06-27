import struct
import subprocess
from pathlib import Path

import imagehash
from PIL import Image

from video_app.core.ffmpeg import popen

FRAME_SIZE = 32
_FRAME_BYTES = FRAME_SIZE * FRAME_SIZE
_TARGET_FRAMES = 150
_MIN_FPS = 0.1
_MAX_FPS = 1.0
_SUBPROCESS_TIMEOUT = 300


def _desired_fps(duration: float) -> float:
    if duration <= 0:
        return _MIN_FPS
    fps = _TARGET_FRAMES / duration
    return max(_MIN_FPS, min(_MAX_FPS, fps))


def extract_at_fps(path: Path, fps: float, ffmpeg_path: Path) -> list[int]:
    """Extract frame pHashes at a specific frames-per-second rate."""
    if fps <= 0:
        return []
    vf = f"fps={fps:.6f},scale={FRAME_SIZE}:{FRAME_SIZE}"
    cmd = [
        str(ffmpeg_path),
        "-hide_banner",
        "-loglevel", "error",
        "-nostdin",
        "-i", str(path),
        "-an",
        "-vf", vf,
        "-pix_fmt", "gray",
        "-f", "rawvideo",
        "-",
    ]
    try:
        proc = popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        raw, _ = proc.communicate(timeout=_SUBPROCESS_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return []
    except OSError:
        return []
    if proc.returncode != 0 or not raw:
        return []

    frames = len(raw) // _FRAME_BYTES
    hashes: list[int] = []
    for i in range(frames):
        chunk = raw[i * _FRAME_BYTES : (i + 1) * _FRAME_BYTES]
        img = Image.frombytes("L", (FRAME_SIZE, FRAME_SIZE), chunk)
        h = imagehash.phash(img)
        hashes.append(_hash_to_int(h))
    return hashes


def extract_frame_hashes(path: Path, duration: float, ffmpeg_path: Path) -> list[int]:
    """Adaptive-fps pHash sequence used by Tier 2 (Advanced)."""
    if duration <= 0:
        return []
    return extract_at_fps(path, _desired_fps(duration), ffmpeg_path)


def _hash_to_int(h: imagehash.ImageHash) -> int:
    n = 0
    for bit in h.hash.flatten():
        n = (n << 1) | (1 if bit else 0)
    return n


def serialize(hashes: list[int]) -> bytes:
    return b"".join(struct.pack("<Q", h) for h in hashes)


def deserialize(blob: bytes) -> list[int]:
    count = len(blob) // 8
    return list(struct.unpack(f"<{count}Q", blob[: count * 8]))


def hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def avg_hamming(a: list[int], b: list[int], max_shift: int = 2) -> float:
    """Lowest average Hamming distance across small time-shift alignments."""
    if not a or not b:
        return 64.0
    best = 64.0
    for shift in range(-max_shift, max_shift + 1):
        if shift >= 0:
            aa, bb = a, b[shift:]
        else:
            aa, bb = a[-shift:], b
        n = min(len(aa), len(bb))
        if n < 5:
            continue
        total = 0
        for i in range(n):
            total += hamming64(aa[i], bb[i])
        best = min(best, total / n)
    return best
