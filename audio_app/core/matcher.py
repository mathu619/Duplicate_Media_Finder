from collections import defaultdict
from pathlib import Path
from typing import Callable

from audio_app.core.cache import FingerprintCache
from audio_app.core.ffmpeg import find_ffprobe, require_fpcalc
from audio_app.core.fingerprint import tier3_audio
from audio_app.core.hasher import full_hash, quick_hash
from audio_app.core.metadata import probe
from audio_app.core.scanner import iter_audio_files
from audio_app.models.duplicate_group import DuplicateGroup, DuplicateKind
from audio_app.models.scan_config import ScanConfig
from audio_app.models.audio_file import AudioFile

ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]

_DEEP_FAST_DURATION_WINDOW = 5.0
_DEEP_FAST_SIMILARITY_THRESHOLD = 0.92
_CONTAINED_MIN_DURATION_DELTA = 2.0
_CONTAINED_SIMILARITY_THRESHOLD = 0.92


def _collect_audio_files(
    config: ScanConfig,
    progress: ProgressCallback,
    is_cancelled: CancelCheck,
) -> list[AudioFile]:
    progress(0, "Walking folders...")
    files: list[AudioFile] = []
    for p in iter_audio_files(config):
        if is_cancelled():
            return []
        try:
            st = p.stat()
        except OSError:
            continue
        files.append(AudioFile(path=p, size=st.st_size, mtime=st.st_mtime))
    return files


def find_byte_identical_duplicates(
    config: ScanConfig,
    cache: FingerprintCache,
    progress: ProgressCallback,
    is_cancelled: CancelCheck,
) -> list[DuplicateGroup]:
    files = _collect_audio_files(config, progress, is_cancelled)

    if not files:
        progress(100, "No audio files found.")
        return []

    progress(5, f"Found {len(files)} audio files. Grouping by size...")

    by_size: dict[int, list[AudioFile]] = defaultdict(list)
    for f in files:
        by_size[f.size].append(f)

    size_candidates = [g for g in by_size.values() if len(g) > 1]
    if not size_candidates:
        progress(100, "No duplicates found.")
        return []

    total_quick = sum(len(g) for g in size_candidates)
    progress(10, f"Quick-hashing {total_quick} candidate files...")

    processed = 0
    by_quick: dict[tuple[int, str], list[AudioFile]] = defaultdict(list)
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
                progress(pct, f"Quick-hashing {processed}/{total_quick}...")

    quick_candidates = [g for g in by_quick.values() if len(g) > 1]
    if not quick_candidates:
        progress(100, "No duplicates found.")
        return []

    total_full = sum(len(g) for g in quick_candidates)
    progress(50, f"Confirming {total_full} candidates with full hash...")

    processed = 0
    by_full: dict[tuple[int, str], list[AudioFile]] = defaultdict(list)
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
                progress(pct, f"Full-hashing {processed}/{total_full}...")

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


def _get_or_compute_metadata(
    f: AudioFile, cache: FingerprintCache, ffprobe_path: Path
):
    path_str = str(f.path)
    meta = cache.get_metadata(path_str, f.size, f.mtime)
    if meta is None:
        meta = probe(f.path, ffprobe_path)
        if meta is not None:
            cache.put_metadata(path_str, f.size, f.mtime, meta)
    return meta


def _get_or_compute_audio_fingerprint(
    f: AudioFile, cache: FingerprintCache, fpcalc_path: Path
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
    fpcalc_path = require_fpcalc()
    ffprobe_path = find_ffprobe()
    files = _collect_audio_files(config, progress, is_cancelled)

    if not files:
        progress(100, "No audio files found.")
        return []

    if ffprobe_path is not None:
        progress(3, f"Found {len(files)} audio files. Reading metadata...")
        for i, f in enumerate(files):
            if is_cancelled():
                return []
            f.metadata = _get_or_compute_metadata(f, cache, ffprobe_path)
            if (i + 1) % 25 == 0 or i + 1 == len(files):
                pct = 3 + int(7 * (i + 1) / len(files))
                progress(pct, f"Reading metadata {i + 1}/{len(files)}...")
    else:
        progress(10, f"Found {len(files)} audio files.")

    progress(10, f"Fingerprinting audio for {len(files)} files...")
    fingerprints: list[tuple[AudioFile, float, list[int]]] = []
    for i, f in enumerate(files):
        if is_cancelled():
            return []
        result = _get_or_compute_audio_fingerprint(f, cache, fpcalc_path)
        if result is not None:
            duration, fp_ints = result
            fingerprints.append((f, duration, fp_ints))
        pct = 10 + int(75 * (i + 1) / len(files))
        progress(pct, f"Audio fingerprinting {i + 1}/{len(files)}...")

    if len(fingerprints) < 2:
        progress(100, "Not enough audio files with fingerprints to compare.")
        return []

    progress(85, "Matching...")
    fingerprints.sort(key=lambda x: x[1])
    uf = _UnionFind(len(fingerprints))
    comparisons = 0
    for i in range(len(fingerprints)):
        if is_cancelled():
            return []
        _, di, fpi = fingerprints[i]
        for j in range(i + 1, len(fingerprints)):
            _, dj, fpj = fingerprints[j]
            if dj - di > _DEEP_FAST_DURATION_WINDOW:
                break
            if tier3_audio.audio_similarity(fpi, fpj) >= _DEEP_FAST_SIMILARITY_THRESHOLD:
                uf.union(i, j)
            comparisons += 1
            if comparisons % 500 == 0:
                progress(85, f"Matching... ({comparisons} pairs compared)")

    groups_map: dict[int, list[AudioFile]] = defaultdict(list)
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


def find_contained_audio_clips(
    config: ScanConfig,
    cache: FingerprintCache,
    progress: ProgressCallback,
    is_cancelled: CancelCheck,
) -> list[DuplicateGroup]:
    fpcalc_path = require_fpcalc()
    ffprobe_path = find_ffprobe()
    files = _collect_audio_files(config, progress, is_cancelled)

    if not files:
        progress(100, "No audio files found.")
        return []

    if ffprobe_path is not None:
        progress(3, f"Found {len(files)} audio files. Reading metadata...")
        for i, f in enumerate(files):
            if is_cancelled():
                return []
            f.metadata = _get_or_compute_metadata(f, cache, ffprobe_path)
            if (i + 1) % 25 == 0 or i + 1 == len(files):
                pct = 3 + int(7 * (i + 1) / len(files))
                progress(pct, f"Reading metadata {i + 1}/{len(files)}...")
    else:
        progress(10, f"Found {len(files)} audio files.")

    progress(10, f"Fingerprinting audio for {len(files)} files...")
    fingerprints: list[tuple[AudioFile, float, list[int]]] = []
    for i, f in enumerate(files):
        if is_cancelled():
            return []
        result = _get_or_compute_audio_fingerprint(f, cache, fpcalc_path)
        if result is not None:
            duration, fp_ints = result
            fingerprints.append((f, duration, fp_ints))
        pct = 10 + int(60 * (i + 1) / len(files))
        progress(pct, f"Audio fingerprinting {i + 1}/{len(files)}...")

    if len(fingerprints) < 2:
        progress(100, "Not enough audio files with fingerprints to compare.")
        return []

    fingerprints.sort(key=lambda x: x[1])
    candidate_pairs: list[tuple[int, int]] = []
    for i, (_, short_duration, short_fp) in enumerate(fingerprints):
        if len(short_fp) < 40:
            continue
        for j in range(i + 1, len(fingerprints)):
            _, long_duration, long_fp = fingerprints[j]
            if long_duration - short_duration < _CONTAINED_MIN_DURATION_DELTA:
                continue
            if len(short_fp) <= len(long_fp):
                candidate_pairs.append((i, j))

    if not candidate_pairs:
        progress(100, "No shorter clips to compare.")
        return []

    progress(70, f"Matching contained clips... (0/{len(candidate_pairs)} pairs)")
    contained_in: dict[int, list[int]] = defaultdict(list)
    best_scores: dict[tuple[int, int], float] = {}
    for done, (short_idx, long_idx) in enumerate(candidate_pairs, start=1):
        if is_cancelled():
            return []
        _, _, short_fp = fingerprints[short_idx]
        _, _, long_fp = fingerprints[long_idx]
        _, similarity = tier3_audio.best_contained_similarity(short_fp, long_fp)
        if similarity >= _CONTAINED_SIMILARITY_THRESHOLD:
            contained_in[short_idx].append(long_idx)
            best_scores[(short_idx, long_idx)] = similarity
        if done % 10 == 0 or done == len(candidate_pairs):
            pct = 70 + int(28 * done / len(candidate_pairs))
            progress(pct, f"Matching contained clips... ({done}/{len(candidate_pairs)} pairs)")

    groups: list[DuplicateGroup] = []
    for short_idx, long_indices in contained_in.items():
        short_file = fingerprints[short_idx][0]
        containing_files = sorted(
            (fingerprints[i][0] for i in long_indices),
            key=lambda f: (f.metadata.duration if f.metadata else f.size, str(f.path)),
            reverse=True,
        )
        best = max(best_scores[(short_idx, i)] for i in long_indices)
        groups.append(
            DuplicateGroup(
                files=[short_file, *containing_files],
                reason=f"Contained audio clip ({best:.0%} match)",
                kind=DuplicateKind.CONTAINED_CLIP,
            )
        )

    groups.sort(
        key=lambda g: (
            g.files[0].metadata.duration if g.files[0].metadata else 0,
            g.wasted_space,
        ),
        reverse=True,
    )
    progress(100, f"Found {len(groups)} contained clip group(s).")
    return groups
