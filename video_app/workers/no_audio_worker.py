from PySide6.QtCore import QThread, Signal

from video_app.core.cache import FingerprintCache
from video_app.core.ffmpeg import FFmpegNotFound, require_ffmpeg
from video_app.core.metadata import probe
from video_app.core.scanner import iter_video_files
from video_app.models.scan_config import ScanConfig
from video_app.models.video_file import VideoFile


class NoAudioWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(object)  # list[VideoFile]
    failed = Signal(str)

    def __init__(self, config: ScanConfig) -> None:
        super().__init__()
        self._config = config
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        cache: FingerprintCache | None = None
        try:
            _, ffprobe_path = require_ffmpeg()
            cache = FingerprintCache()

            self.progress.emit(0, "Walking folders…")
            files: list[VideoFile] = []
            for p in iter_video_files(self._config):
                if self._cancel_requested:
                    self.finished.emit([])
                    return
                try:
                    st = p.stat()
                except OSError:
                    continue
                files.append(VideoFile(path=p, size=st.st_size, mtime=st.st_mtime))

            if not files:
                self.finished.emit([])
                return

            no_audio: list[VideoFile] = []
            for i, f in enumerate(files):
                if self._cancel_requested:
                    self.finished.emit(no_audio)
                    return
                path_str = str(f.path)
                meta = cache.get_metadata(path_str, f.size, f.mtime)
                if meta is None:
                    meta = probe(f.path, ffprobe_path)
                    if meta is not None:
                        cache.put_metadata(path_str, f.size, f.mtime, meta)
                if meta is not None:
                    f.metadata = meta
                    if meta.audio_codec is None:
                        no_audio.append(f)
                if (i + 1) % 10 == 0 or i + 1 == len(files):
                    pct = int(100 * (i + 1) / len(files))
                    self.progress.emit(pct, f"Checking {i + 1}/{len(files)}…")

            self.finished.emit(no_audio)
        except FFmpegNotFound as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
        finally:
            if cache is not None:
                cache.close()
