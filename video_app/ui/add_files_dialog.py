from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from video_app.core.scanner import VIDEO_EXTENSIONS, is_video_file
from video_app.ui.theme_helpers import (
    paint_dark_gradient,
    panel_drop_shadow,
    setup_dark_palette,
)


def _video_filter() -> str:
    exts = " ".join(f"*{e}" for e in sorted(VIDEO_EXTENSIONS))
    return f"Video files ({exts});;All files (*)"


class AddFilesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add files to scan")
        self.setModal(True)
        self.resize(640, 420)
        setup_dark_palette(self)

        self._paths: list[str] = []

        intro = QLabel(
            "Paste one file path per line, or use Browse to pick files. "
            "Only existing video files are added."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: rgba(255,255,255,160); background: transparent;")

        self._textarea = QPlainTextEdit()
        self._textarea.setPlaceholderText(
            "C:/Users/you/Videos/clip1.mp4\nD:/Movies/clip2.mkv"
        )

        textarea_layout = QVBoxLayout()
        textarea_layout.setContentsMargins(14, 14, 14, 14)
        textarea_layout.addWidget(self._textarea)

        textarea_panel = QFrame()
        textarea_panel.setObjectName("glassPanel")
        textarea_panel.setLayout(textarea_layout)
        textarea_panel.setGraphicsEffect(panel_drop_shadow(self))

        browse_btn = QPushButton("Browse files…")
        browse_btn.clicked.connect(self._on_browse)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        add_btn = QPushButton("Add")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._on_ok)

        bottom = QHBoxLayout()
        bottom.addWidget(browse_btn)
        bottom.addStretch()
        bottom.addWidget(cancel_btn)
        bottom.addWidget(add_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(intro)
        layout.addWidget(textarea_panel, stretch=1)
        layout.addLayout(bottom)
        self.setLayout(layout)

    @property
    def paths(self) -> list[str]:
        return self._paths

    def paintEvent(self, _event) -> None:
        paint_dark_gradient(self)

    def _on_browse(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Pick video files", "", _video_filter()
        )
        if not files:
            return
        existing = self._textarea.toPlainText().rstrip()
        block = "\n".join(files)
        merged = (existing + "\n" + block).strip() if existing else block
        self._textarea.setPlainText(merged)

    def _on_ok(self) -> None:
        text = self._textarea.toPlainText()
        candidates = [
            line.strip().strip('"').strip("'")
            for line in text.splitlines()
            if line.strip()
        ]
        valid: list[str] = []
        seen: set[str] = set()
        invalid_count = 0
        for c in candidates:
            try:
                p = Path(c)
            except OSError:
                invalid_count += 1
                continue
            key = str(p).lower()
            if key in seen:
                continue
            if p.exists() and p.is_file() and is_video_file(p.name):
                valid.append(str(p))
                seen.add(key)
            else:
                invalid_count += 1
        if not valid:
            QMessageBox.warning(
                self,
                "No valid videos",
                "None of the paths point to existing video files.",
            )
            return
        if invalid_count:
            QMessageBox.information(
                self,
                "Some paths skipped",
                f"Adding {len(valid)} file(s). "
                f"Skipped {invalid_count} (path missing or not a recognized video).",
            )
        self._paths = valid
        self.accept()
