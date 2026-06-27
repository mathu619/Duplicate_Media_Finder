from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from audio_app.models.duplicate_group import DuplicateGroup
from audio_app.workers.scan_worker import ScanWorker


class ProgressDialog(QDialog):
    def __init__(self, worker: ScanWorker, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scanning…")
        self.setModal(True)
        self.resize(520, 160)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._worker = worker
        self._groups: list[DuplicateGroup] = []
        self._error: str | None = None
        self._finished = False
        self._cancel_requested = False

        self._status = QLabel("Preparing…")
        self._status.setWordWrap(True)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)

        layout = QVBoxLayout()
        layout.addWidget(self._status)
        layout.addWidget(self._bar)
        layout.addWidget(self._cancel_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.start()

    @property
    def groups(self) -> list[DuplicateGroup]:
        return self._groups

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def cancelled(self) -> bool:
        return self._cancel_requested

    @property
    def worker(self) -> ScanWorker:
        return self._worker

    def _on_progress(self, percent: int, message: str) -> None:
        self._bar.setValue(max(0, min(100, percent)))
        self._status.setText(message)

    def _on_finished(self, groups) -> None:
        self._groups = groups or []
        self._finished = True
        if self._cancel_requested:
            self.reject()
        else:
            self.accept()

    def _on_failed(self, error: str) -> None:
        self._error = error
        self._finished = True
        self.reject()

    def _on_cancel(self) -> None:
        self._cancel_requested = True
        self._worker.request_cancel()
        self._status.setText("Cancelling…")
        self._cancel_btn.setEnabled(False)

    def closeEvent(self, event) -> None:
        if not self._finished:
            self._worker.request_cancel()
            self._cancel_requested = True
            self._status.setText("Cancelling...")
            self._cancel_btn.setEnabled(False)
            event.ignore()
            return
        super().closeEvent(event)
