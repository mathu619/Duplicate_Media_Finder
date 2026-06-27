import struct
from pathlib import Path

import numpy as np

from video_app.core.fingerprint.tier2_frames import extract_at_fps

UNIFORM_FPS = 1.0  # one frame per second; fixed so timelines align across videos
MIN_SAMPLES = 15
_FULL_BITS = 64


def extract_uniform_frame_hashes(path: Path, ffmpeg_path: Path) -> list[int]:
    return extract_at_fps(path, UNIFORM_FPS, ffmpeg_path)


def serialize(hashes: list[int]) -> bytes:
    return b"".join(struct.pack("<Q", h & 0xFFFFFFFFFFFFFFFF) for h in hashes)


def deserialize(blob: bytes) -> list[int]:
    count = len(blob) // 8
    return list(struct.unpack(f"<{count}Q", blob[: count * 8]))


def to_numpy(hashes: list[int]) -> np.ndarray:
    return np.asarray(hashes, dtype=np.uint64)


def _popcount_u64(arr: np.ndarray) -> np.ndarray:
    m1 = np.uint64(0x5555555555555555)
    m2 = np.uint64(0x3333333333333333)
    m4 = np.uint64(0x0F0F0F0F0F0F0F0F)
    h01 = np.uint64(0x0101010101010101)
    x = arr - ((arr >> np.uint64(1)) & m1)
    x = (x & m2) + ((x >> np.uint64(2)) & m2)
    x = (x + (x >> np.uint64(4))) & m4
    return (x * h01) >> np.uint64(56)


def aligned_avg_hamming(a: np.ndarray, b: np.ndarray) -> float:
    """Compare from offset 0 on both sides, truncating to the shorter length."""
    n = min(len(a), len(b))
    if n < MIN_SAMPLES:
        return float(_FULL_BITS)
    bits = int(_popcount_u64(a[:n] ^ b[:n]).sum())
    return bits / n


def best_contained_alignment(short_fp: np.ndarray, long_fp: np.ndarray) -> tuple[int, float]:
    """Slide the shorter fingerprint across the longer, return (offset, avg_hamming)."""
    ns = len(short_fp)
    nl = len(long_fp)
    if ns < MIN_SAMPLES or ns > nl:
        return 0, float(_FULL_BITS)
    best_offset = 0
    best_avg = float(_FULL_BITS)
    # Sliding window; numpy vectorized per offset
    for k in range(nl - ns + 1):
        bits = int(_popcount_u64(short_fp ^ long_fp[k : k + ns]).sum())
        avg = bits / ns
        if avg < best_avg:
            best_avg = avg
            best_offset = k
            if best_avg < 1.0:
                break
    return best_offset, best_avg
