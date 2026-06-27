from collections import defaultdict
from pathlib import Path
from typing import Callable

from video_app.core.cache import FingerprintCache
from video_app.core.ffmpeg import require_ffmpeg, require_fpcalc
from video_app.core.fingerprint.tier2_frames import (
    avg_hamming,
    deserialize,
    extract_frame_hashes,
    serialize,
)
from video_app.core.fingerprint import tier3_audio, tier3_video
from video_app.core.hasher import full_hash, quick_hash
from video_app.core.metadata import probe
from video_app.core.scanner import iter_video_files
from video_app.models.duplicate_group import DuplicateGroup, DuplicateKind
from video_app.models.scan_config import ScanConfig
from video_app.models.video_file import VideoFile

ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]

# Tier 2 tuning
_TIER2_DURATION_WINDOW = 5.0    # seconds; pair candidates within this duration delta
_TIER2_MATCH_THRESHOLD = 10.0   # avg Hamming distance (out of 64) below which we call it a match

# Tier 3 Fast tuning
_TIER3_FAST_DURATION_WINDOW = 5.0
_TIER3_FAST_SIMILARITY_THRESHOLD = 0.92  # 0-1; higher = stricter

# Tier 3 Slow tuning
_TIER3_SLOW_ALIGNED_WINDOW = 5.0        # seconds; treat as aligned if duration diff below this
_TIER3_SLOW_MATCH_BITS = 10.0           # avg Hamming (out of 64) below which we call it a match
_TIER3_SLOW_CONTAINED_RATIO = 0.8       # len(short)/len(long) >= this means "same content edit"


def find_byte_identical_duplicates(
    config: ScanConfig,
    cache: FingerprintCache,
    progress: ProgressCallback,
    is_cancelled: CancelCheck,
) -> list[DuplicateGroup]:
    progress(0, "Walking folders…")
    files: list[VideoFile] = []
    for p in iter_video_files(config):
        if is_cancelled():
            return []
        try:
            st = p.stat()
        except OSError:
            continue
        files.append(VideoFile(path=p, size=st.st_size, mtime=st.st_mtime))

    if not files:
        progress(100, "No video files found.")
        return []

    progress(5, f"Found {len(files)} video files. Grouping by size…")

    by_size: dict[int, list[VideoFile]] = defaultdict(list)
    for f in files:
        by_size[f.size].append(f)

    size_candidates = [g for g in by_size.values() if len(g) > 1]
    if not size_candidates:
        progress(100, "No duplicates found.")
        return []

    total_quick = sum(len(g) for g in size_candidates)
    progress(10, f"Quick-hashing {total_quick} candidate files…")

    processed = 0
    by_quick: dict[tuple[int, str], list[VideoFile]] = defaultdict(list)
    for group in size_candidates:
        for f in group:
            if is_cancelled():
                return []
            path_str = str(f.path)
            cached = cache.get_hashes(path_str, f.size, f.mtime)
            qh = cached[0] if cached else None
            fh = cached[1] if cached else None
            if not qh:
                try:
                    qh = quick_hash(f.path, f.size)
                except OSError:
                    processed += 1
                    continue
                cache.put_hashes(path_str, f.size, f.mtime, qh, fh)
            by_quick[(f.size, qh)].append(f)
            processed += 1
            if processed % 10 == 0 or processed == total_quick:
                pct = 10 + int(40 * processed / total_quick)
                progress(pct, f"Quick-hashing {processed}/{total_quick}…")

    quick_candidates = [g for g in by_quick.values() if len(g) > 1]
    if not quick_candidates:
        progress(100, "No duplicates found.")
        return []

    total_full = sum(len(g) for g in quick_candidates)
    progress(50, f"Confirming {total_full} candidates with full hash…")

    processed = 0
    by_full: dict[tuple[int, str], list[VideoFile]] = defaultdict(list)
    for group in quick_candidates:
        for f in group:
            if is_cancelled():
                return []
            path_str = str(f.path)
            cached = cache.get_hashes(path_str, f.size, f.mtime)
            qh = cached[0] if cached else None
            fh = cached[1] if cached else None
            if not fh:
                try:
                    fh = full_hash(f.path)
                except OSError:
                    processed += 1
                    continue
                cache.put_hashes(path_str, f.size, f.mtime, qh, fh)
            by_full[(f.size, fh)].append(f)
            processed += 1
            if processed % 5 == 0 or processed == total_full:
                pct = 50 + int(45 * processed / total_full)
                progress(pct, f"Full-hashing {processed}/{total_full}…")

    groups = [
        DuplicateGroup(files=sorted(g, key=lambda f: str(f.path)), reason="Byte-identical")
        for g in by_full.values()
        if len(g) > 1
    ]
    groups.sort(key=lambda g: g.wasted_space, reverse=True)
    progress(100, f"Found {len(groups)} duplicate group(s).")
    return groups


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1


def _get_or_compute_metadata(f: VideoFile, cache: FingerprintCache, ffprobe_path: Path):
    path_str = str(f.path)
    meta = cache.get_metadata(path_str, f.size, f.mtime)
    if meta is None:
        meta = probe(f.path, ffprobe_path)
        if meta is not None:
            cache.put_metadata(path_str, f.size, f.mtime, meta)
    return meta


def _get_or_compute_fingerprint(
    f: VideoFile, cache: FingerprintCache, ffmpeg_path: Path, duration: float
) -> list[int]:
    path_str = str(f.path)
    blob = cache.get_frame_fingerprint(path_str, f.size, f.mtime)
    if blob is not None:
        return deserialize(blob)
    hashes = extract_frame_hashes(f.path, duration, ffmpeg_path)
    if hashes:
        cache.put_frame_fingerprint(path_str, f.size, f.mtime, serialize(hashes))
    return hashes


def find_visually_similar_duplicates(
    config: ScanConfig,
    cache: FingerprintCache,
    progress: ProgressCallback,
    is_cancelled: CancelCheck,
) -> list[DuplicateGroup]:
    ffmpeg_path, ffprobe_path = require_ffmpeg()

    progress(0, "Walking folders…")
    files: list[VideoFile] = []
    for p in iter_video_files(config):
        if is_cancelled():
            return []
        try:
            st = p.stat()
        except OSError:
            continue
        files.append(VideoFile(path=p, size=st.st_size, mtime=st.st_mtime))

    if not files:
        progress(100, "No video files found.")
        return []

    progress(3, f"Found {len(files)} video files. Reading metadata…")
    for i, f in enumerate(files):
        if is_cancelled():
            return []
        f.metadata = _get_or_compute_metadata(f, cache, ffprobe_path)
        if (i + 1) % 25 == 0 or i + 1 == len(files):
            pct = 3 + int(7 * (i + 1) / len(files))
            progress(pct, f"Reading metadata {i + 1}/{len(files)}…")

    usable = [f for f in files if f.metadata and f.metadata.duration > 0]
    if not usable:
        progress(100, "No videos with readable duration.")
        return []

    progress(10, f"Fingerprinting {len(usable)} videos…")
    fingerprints: list[tuple[VideoFile, list[int]]] = []
    for i, f in enumerate(usable):
        if is_cancelled():
            return []
        hashes = _get_or_compute_fingerprint(f, cache, ffmpeg_path, f.metadata.duration)
        if hashes:
            fingerprints.append((f, hashes))
        pct = 10 + int(75 * (i + 1) / len(usable))
        progress(pct, f"Fingerprinting {i + 1}/{len(usable)}…")

    if len(fingerprints) < 2:
        progress(100, "Not enough fingerprinted videos to compare.")
        return []

    progress(85, "Matching…")
    fingerprints.sort(key=lambda x: x[0].metadata.duration)
    uf = _UnionFind(len(fingerprints))
    comparisons = 0
    for i in range(len(fingerprints)):
        if is_cancelled():
            return []
        fi, hi = fingerprints[i]
        for j in range(i + 1, len(fingerprints)):
            fj, hj = fingerprints[j]
            if fj.metadata.duration - fi.metadata.duration > _TIER2_DURATION_WINDOW:
                break
            if avg_hamming(hi, hj) <= _TIER2_MATCH_THRESHOLD:
                uf.union(i, j)
            comparisons += 1
            if comparisons % 500 == 0:
                progress(85, f"Matching… ({comparisons} pairs compared)")

    groups_map: dict[int, list[VideoFile]] = defaultdict(list)
    for i, (f, _) in enumerate(fingerprints):
        groups_map[uf.find(i)].append(f)

    groups = [
        DuplicateGroup(
            files=sorted(g, key=lambda f: str(f.path)),
            reason="Visually similar",
        )
        for g in groups_map.values()
        if len(g) > 1
    ]
    groups.sort(key=lambda g: g.wasted_space, reverse=True)
    progress(100, f"Found {len(groups)} duplicate group(s).")
    return groups


def _get_or_compute_audio_fingerprint(
    f: VideoFile, cache: FingerprintCache, fpcalc_path: Path
) -> tuple[float, list[int]] | None:
    path_str = str(f.path)
    cached = cache.get_audio_fingerprint(path_str, f.size, f.mtime)
    if cached is not None:
        return (cached[0], tier3_audio.deserialize(cached[1]))
    result = tier3_audio.extract_audio_fingerprint(f.path, fpcalc_path)
    if result is None:
        return None
    duration, fingerprint = result
    cache.put_audio_fingerprint(
        path_str, f.size, f.mtime, duration, tier3_audio.serialize(fingerprint)
    )
    return (duration, fingerprint)


def find_audio_duplicates(
    config: ScanConfig,
    cache: FingerprintCache,
    progress: ProgressCallback,
    is_cancelled: CancelCheck,
) -> list[DuplicateGroup]:
    _, ffprobe_path = require_ffmpeg()
    fpcalc_path = require_fpcalc()

    progress(0, "Walking folders…")
    files: list[VideoFile] = []
    for p in iter_video_files(config):
        if is_cancelled():
            return []
        try:
            st = p.stat()
        except OSError:
            continue
        files.append(VideoFile(path=p, size=st.st_size, mtime=st.st_mtime))

    if not files:
        progress(100, "No video files found.")
        return []

    progress(3, f"Found {len(files)} video files. Reading metadata…")
    for i, f in enumerate(files):
        if is_cancelled():
            return []
        f.metadata = _get_or_compute_metadata(f, cache, ffprobe_path)
        if (i + 1) % 25 == 0 or i + 1 == len(files):
            pct = 3 + int(7 * (i + 1) / len(files))
            progress(pct, f"Reading metadata {i + 1}/{len(files)}…")

    progress(10, f"Fingerprinting audio for {len(files)} videos…")
    fingerprints: list[tuple[VideoFile, float, list[int]]] = []
    for i, f in enumerate(files):
        if is_cancelled():
            return []
        result = _get_or_compute_audio_fingerprint(f, cache, fpcalc_path)
        if result is not None:
            duration, fp_ints = result
            fingerprints.append((f, duration, fp_ints))
        pct = 10 + int(75 * (i + 1) / len(files))
        progress(pct, f"Audio fingerprinting {i + 1}/{len(files)}…")

    if len(fingerprints) < 2:
        progress(100, "Not enough videos with audio fingerprints to compare.")
        return []

    progress(85, "Matching…")
    fingerprints.sort(key=lambda x: x[1])
    uf = _UnionFind(len(fingerprints))
    comparisons = 0
    for i in range(len(fingerprints)):
        if is_cancelled():
            return []
        _, di, fpi = fingerprints[i]
        for j in range(i + 1, len(fingerprints)):
            _, dj, fpj = fingerprints[j]
            if dj - di > _TIER3_FAST_DURATION_WINDOW:
                break
            if tier3_audio.audio_similarity(fpi, fpj) >= _TIER3_FAST_SIMILARITY_THRESHOLD:
                uf.union(i, j)
            comparisons += 1
            if comparisons % 500 == 0:
                progress(85, f"Matching… ({comparisons} pairs compared)")

    groups_map: dict[int, list[VideoFile]] = defaultdict(list)
    for i, (f, _, _) in enumerate(fingerprints):
        groups_map[uf.find(i)].append(f)

    groups = [
        DuplicateGroup(
            files=sorted(g, key=lambda f: str(f.path)),
            reason="Same audio",
        )
        for g in groups_map.values()
        if len(g) > 1
    ]
    groups.sort(key=lambda g: g.wasted_space, reverse=True)
    progress(100, f"Found {len(groups)} duplicate group(s).")
    return groups


def _get_or_compute_uniform_fingerprint(
    f: VideoFile, cache: FingerprintCache, ffmpeg_path: Path
) -> list[int]:
    path_str = str(f.path)
    blob = cache.get_uniform_frame_fingerprint(path_str, f.size, f.mtime)
    if blob is not None:
        return tier3_video.deserialize(blob)
    hashes = tier3_video.extract_uniform_frame_hashes(f.path, ffmpeg_path)
    if hashes:
        cache.put_uniform_frame_fingerprint(
            path_str, f.size, f.mtime, tier3_video.serialize(hashes)
        )
    return hashes


def find_temporally_aligned_duplicates(
    config: ScanConfig,
    cache: FingerprintCache,
    progress: ProgressCallback,
    is_cancelled: CancelCheck,
) -> list[DuplicateGroup]:
    ffmpeg_path, ffprobe_path = require_ffmpeg()

    progress(0, "Walking folders…")
    files: list[VideoFile] = []
    for p in iter_video_files(config):
        if is_cancelled():
            return []
        try:
            st = p.stat()
        except OSError:
            continue
        files.append(VideoFile(path=p, size=st.st_size, mtime=st.st_mtime))

    if not files:
        progress(100, "No video files found.")
        return []

    progress(3, f"Found {len(files)} video files. Reading metadata…")
    for i, f in enumerate(files):
        if is_cancelled():
            return []
        f.metadata = _get_or_compute_metadata(f, cache, ffprobe_path)
        if (i + 1) % 25 == 0 or i + 1 == len(files):
            pct = 3 + int(5 * (i + 1) / len(files))
            progress(pct, f"Reading metadata {i + 1}/{len(files)}…")

    usable = [f for f in files if f.metadata and f.metadata.duration > 0]
    if len(usable) < 2:
        progress(100, "Need at least two videos with readable duration.")
        return []

    progress(8, f"Fingerprinting {len(usable)} videos at 1 fps…")
    prints: list[tuple[VideoFile, list[int]]] = []
    for i, f in enumerate(usable):
        if is_cancelled():
            return []
        hashes = _get_or_compute_uniform_fingerprint(f, cache, ffmpeg_path)
        if len(hashes) >= tier3_video.MIN_SAMPLES:
            prints.append((f, hashes))
        pct = 8 + int(62 * (i + 1) / len(usable))
        progress(pct, f"Fingerprinting {i + 1}/{len(usable)}…")

    if len(prints) < 2:
        progress(100, "Not enough fingerprinted videos to compare.")
        return []

    progress(70, "Matching…")
    # Sort by fingerprint length (== duration in seconds at 1 fps); shorter first.
    prints.sort(key=lambda x: len(x[1]))
    np_fps = [tier3_video.to_numpy(h) for _, h in prints]

    uf = _UnionFind(len(prints))
    contained_in: dict[int, set[int]] = defaultdict(set)  # short_idx -> {long_idx}

    total_pairs = len(prints) * (len(prints) - 1) // 2
    done = 0
    for i in range(len(prints)):
        if is_cancelled():
            return []
        for j in range(i + 1, len(prints)):
            done += 1
            ns = len(np_fps[i])
            nl = len(np_fps[j])
            # ns <= nl because prints are sorted by length
            if abs(nl - ns) <= _TIER3_SLOW_ALIGNED_WINDOW:
                avg = tier3_video.aligned_avg_hamming(np_fps[i], np_fps[j])
                if avg <= _TIER3_SLOW_MATCH_BITS:
                    uf.union(i, j)
                else:
                    # Aligned compare assumes the trim is at the end. If the
                    # short clip was front-trimmed (intro/leader/ads cut), every
                    # frame is shifted and avg Hamming explodes. Slide to find
                    # the real offset; duration ratio is still above the
                    # contained threshold, so keep it as SAME_CONTENT.
                    _, slid_avg = tier3_video.best_contained_alignment(
                        np_fps[i], np_fps[j]
                    )
                    if slid_avg <= _TIER3_SLOW_MATCH_BITS:
                        uf.union(i, j)
            else:
                _, avg = tier3_video.best_contained_alignment(np_fps[i], np_fps[j])
                if avg <= _TIER3_SLOW_MATCH_BITS:
                    ratio = ns / nl if nl else 0.0
                    if ratio >= _TIER3_SLOW_CONTAINED_RATIO:
                        uf.union(i, j)
                    else:
                        contained_in[i].add(j)
            if done % 50 == 0:
                pct = 70 + int(28 * done / max(1, total_pairs))
                progress(pct, f"Matching… ({done}/{total_pairs} pairs)")

    # Build SAME_CONTENT groups
    groups_map: dict[int, list[int]] = defaultdict(list)
    for idx in range(len(prints)):
        groups_map[uf.find(idx)].append(idx)

    groups: list[DuplicateGroup] = []
    for member_indices in groups_map.values():
        if len(member_indices) <= 1:
            continue
        files_in_group = [prints[m][0] for m in member_indices]
        groups.append(
            DuplicateGroup(
                files=sorted(files_in_group, key=lambda f: str(f.path)),
                reason="Same content",
                kind=DuplicateKind.SAME_CONTENT,
            )
        )

    # Build CONTAINED_CLIP groups: for each short clip, the longer videos it lives inside.
    # Collapse the longer videos to their SAME_CONTENT representative so we don't list
    # three near-identical copies of the same movie separately.
    rep_to_idx: dict[int, int] = {}
    for idx in range(len(prints)):
        rep = uf.find(idx)
        rep_to_idx.setdefault(rep, idx)

    for short_idx, long_idxs in contained_in.items():
        short_rep = uf.find(short_idx)
        canonical_longs: list[int] = []
        seen_reps: set[int] = set()
        for li in long_idxs:
            long_rep = uf.find(li)
            if long_rep == short_rep or long_rep in seen_reps:
                continue
            seen_reps.add(long_rep)
            canonical_longs.append(rep_to_idx[long_rep])
        if not canonical_longs:
            continue
        files_in_group = [prints[short_idx][0]] + [prints[c][0] for c in canonical_longs]
        groups.append(
            DuplicateGroup(
                files=files_in_group,
                reason="Shorter clip contained in longer video(s)",
                kind=DuplicateKind.CONTAINED_CLIP,
            )
        )

    groups.sort(key=lambda g: (g.kind.value, -g.wasted_space))
    progress(100, f"Found {len(groups)} duplicate group(s).")
    return groups
