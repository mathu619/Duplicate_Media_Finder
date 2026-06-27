from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from video_app.core.dependencies import status
from video_app.ui.download_dialog import DownloadDialog


class DependenciesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage dependencies")
        self.setModal(True)
        self.resize(520, 260)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        intro = QLabel(
            "These external tools are bundled in the 'vendor' folder. "
            "Download them automatically below, or install them manually."
        )
        intro.setWordWrap(True)

        grid = QGridLayout()
        grid.addWidget(QLabel("<b>Tool</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Status</b>"), 0, 1)
        grid.addWidget(QLabel("<b>Action</b>"), 0, 2)

        self._ffmpeg_status = QLabel()
        self._fpcalc_status = QLabel()

        ffmpeg_btn = QPushButton("Download FFmpeg (~120 MB)")
        ffmpeg_btn.clicked.connect(self._download_ffmpeg)
        fpcalc_btn = QPushButton("Download Chromaprint (~3 MB)")
        fpcalc_btn.clicked.connect(self._download_chromaprint)

        grid.addWidget(QLabel("FFmpeg + ffprobe"), 1, 0)
        grid.addWidget(self._ffmpeg_status, 1, 1)
        grid.addWidget(ffmpeg_btn, 1, 2)

        grid.addWidget(QLabel("Chromaprint (fpcalc)"), 2, 0)
        grid.addWidget(self._fpcalc_status, 2, 1)
        grid.addWidget(fpcalc_btn, 2, 2)

        usage = QLabel(
            "FFmpeg is needed for Advanced and both Deep tiers.\n"
            "Chromaprint is needed only for Deep (Fast)."
        )
        usage.setWordWrap(True)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(intro)
        layout.addSpacing(8)
        layout.addLayout(grid)
        layout.addSpacing(8)
        layout.addWidget(usage)
        layout.addStretch()
        layout.addLayout(bottom)
        self.setLayout(layout)

        self._refresh()

    def _refresh(self) -> None:
        s = status()
        ok_html = "<span style='color: #1a7f1a;'>installed</span>"
        miss_html = "<span style='color: #b00020;'>missing</span>"
        self._ffmpeg_status.setText(ok_html if s["ffmpeg"] and s["ffprobe"] else miss_html)
        self._fpcalc_status.setText(ok_html if s["fpcalc"] else miss_html)

    def _download_ffmpeg(self) -> None:
        dlg = DownloadDialog("ffmpeg", "FFmpeg", parent=self)
        dlg.exec()
        self._refresh()
        if dlg.succeeded:
            QMessageBox.information(self, "Done", "FFmpeg installed.")

    def _download_chromaprint(self) -> None:
        dlg = DownloadDialog("chromaprint", "Chromaprint", parent=self)
        dlg.exec()
        self._refresh()
        if dlg.succeeded:
            QMessageBox.information(self, "Done", "Chromaprint installed.")
