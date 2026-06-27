from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from audio_app.workers.download_worker import DownloadWorker


class DownloadDialog(QDialog):
    """Modal dialog that downloads one bundled binary. .succeeded reflects the outcome."""

    def __init__(self, target: str, friendly_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Downloading {friendly_name}…")
        self.setModal(True)
        self.resize(520, 160)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._succeeded = False
        self._finished = False

        self._status = QLabel(f"Preparing to download {friendly_name}…")
        self._status.setWordWrap(True)
        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # indeterminate until first byte
        self._close_btn = QPushButton("Downloading...")
        self._close_btn.setEnabled(False)
        self._close_btn.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self._status)
        layout.addWidget(self._bar)
        layout.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

        self._worker = DownloadWorker(target)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    @property
    def succeeded(self) -> bool:
        return self._succeeded

    def _on_progress(self, done: int, total: int, message: str) -> None:
        if total > 0:
            if self._bar.maximum() != 100:
                self._bar.setRange(0, 100)
            self._bar.setValue(int(100 * done / total))
        else:
            self._bar.setRange(0, 0)
        self._status.setText(message)

    def _on_finished(self) -> None:
        self._succeeded = True
        self._finished = True
        self.accept()

    def _on_failed(self, error: str) -> None:
        self._finished = True
        QMessageBox.critical(self, "Download failed", error)
        self.reject()

    def reject(self) -> None:
        if not self._finished:
            self._status.setText("Download is still running. Please wait for it to finish.")
            return
        super().reject()

    def closeEvent(self, event) -> None:
        if not self._finished:
            self._status.setText("Download is still running. Please wait for it to finish.")
            event.ignore()
            return
        super().closeEvent(event)
