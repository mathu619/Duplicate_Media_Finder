import time

from PySide6.QtCore import QThread, Signal

from audio_app.core.cache import FingerprintCache
from audio_app.core.ffmpeg import ChromaprintNotFound
from audio_app.core.matcher import (
    find_audio_duplicates,
    find_byte_identical_duplicates,
    find_contained_audio_clips,
)
from audio_app.models.scan_config import DetectionTier, ScanConfig


class ScanWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(object)  # list[DuplicateGroup]
    failed = Signal(str)

    def __init__(self, config: ScanConfig) -> None:
        super().__init__()
        self._config = config
        self._cancel_requested = False
        self._cache_hits = 0
        self._cache_computes = 0
        self._elapsed_seconds = 0.0

    @property
    def cache_hits(self) -> int:
        return self._cache_hits

    @property
    def cache_computes(self) -> int:
        return self._cache_computes

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_seconds

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        cache: FingerprintCache | None = None
        started = time.monotonic()
        try:
            cache = FingerprintCache()
            progress_cb = lambda p, m: self.progress.emit(p, m)  # noqa: E731
            cancel_cb = lambda: self._cancel_requested  # noqa: E731

            tier = self._config.tier
            if tier == DetectionTier.BASIC:
                groups = find_byte_identical_duplicates(self._config, cache, progress_cb, cancel_cb)
            elif tier == DetectionTier.DEEP_FAST:
                groups = find_audio_duplicates(self._config, cache, progress_cb, cancel_cb)
            elif tier == DetectionTier.CONTAINED_CLIPS:
                groups = find_contained_audio_clips(self._config, cache, progress_cb, cancel_cb)
            else:
                raise RuntimeError(f"Unknown detection tier: {tier}")

            if self._cancel_requested:
                self.finished.emit([])
                return
            self.finished.emit(groups)
        except ChromaprintNotFound as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
        finally:
            if cache is not None:
                self._cache_hits = cache.hits
                self._cache_computes = cache.computes
                cache.close()
            self._elapsed_seconds = time.monotonic() - started
