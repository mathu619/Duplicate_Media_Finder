from PySide6.QtCore import QThread, Signal

from video_app.core.dependencies import (
    DependencyDownloadError,
    install_chromaprint,
    install_ffmpeg,
)


class DownloadWorker(QThread):
    progress = Signal(int, int, str)  # bytes_done, bytes_total, message
    finished = Signal()
    failed = Signal(str)

    def __init__(self, target: str) -> None:
        super().__init__()
        self._target = target

    def run(self) -> None:
        cb = lambda done, total, msg: self.progress.emit(done, total, msg)  # noqa: E731
        try:
            if self._target == "ffmpeg":
                install_ffmpeg(cb)
            elif self._target == "chromaprint":
                install_chromaprint(cb)
            else:
                raise RuntimeError(f"Unknown download target: {self._target}")
            self.finished.emit()
        except DependencyDownloadError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Unexpected error: {e}")
