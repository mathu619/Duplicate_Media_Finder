from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from video_app.models.scan_config import ScanConfig
from video_app.ui.centered_icon_delegate import CenteredIconDelegate
from video_app.ui.file_actions import open_in_default_player, show_in_explorer
from video_app.ui.icons import folder_icon
from video_app.ui.theme_helpers import (
    paint_dark_gradient,
    panel_drop_shadow,
    setup_dark_palette,
)
from video_app.workers.no_audio_worker import NoAudioWorker


def _fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _fmt_duration(seconds: float) -> str:
    if seconds <= 0:
        return ""
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{sec:02d}" if h else f"{m:d}:{sec:02d}"


class FindNoAudioDialog(QDialog):
    """Two-page modal: shows scan progress, then results listing audioless videos."""

    def __init__(self, config: ScanConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Videos without audio")
        self.setModal(True)
        self.resize(960, 600)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        setup_dark_palette(self)

        self._results: list = []
        self._stack = QStackedWidget()

        # Progress page
        progress_page = QWidget()
        prog_title = QLabel("SCANNING FOR AUDIOLESS VIDEOS")
        prog_title.setObjectName("sectionLabel")
        self._status = QLabel("Starting…")
        self._status.setWordWrap(True)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)
        prog_inner = QVBoxLayout()
        prog_inner.setContentsMargins(16, 14, 16, 14)
        prog_inner.setSpacing(10)
        prog_inner.addWidget(prog_title)
        prog_inner.addWidget(self._status)
        prog_inner.addWidget(self._bar)
        prog_inner.addStretch()
        prog_inner.addWidget(self._cancel_btn, alignment=Qt.AlignmentFlag.AlignRight)
        prog_panel = QFrame()
        prog_panel.setObjectName("glassPanel")
        prog_panel.setLayout(prog_inner)
        prog_panel.setGraphicsEffect(panel_drop_shadow(self))
        prog_outer = QVBoxLayout()
        prog_outer.setContentsMargins(20, 20, 20, 20)
        prog_outer.addWidget(prog_panel, stretch=1)
        progress_page.setLayout(prog_outer)

        # Results page
        results_page = QWidget()
        res_title = QLabel("VIDEOS WITHOUT AUDIO")
        res_title.setObjectName("sectionLabel")
        self._summary = QLabel()
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["File", "Size", "Duration", ""])
        self._tree.setRootIsDecorated(False)
        self._tree.setIndentation(0)
        header = self._tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._tree.setColumnWidth(1, 90)
        self._tree.setColumnWidth(2, 80)
        self._tree.setColumnWidth(3, 44)
        self._tree.setFrameShape(QFrame.Shape.NoFrame)
        self._tree.setStyleSheet("QTreeWidget { background: transparent; border: none; }")
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemClicked.connect(self._on_item_click)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.setIconSize(QSize(26, 26))
        self._tree.setItemDelegateForColumn(
            3, CenteredIconDelegate(QSize(26, 26), self._tree)
        )

        res_inner = QVBoxLayout()
        res_inner.setContentsMargins(16, 14, 16, 14)
        res_inner.setSpacing(10)
        res_inner.addWidget(res_title)
        res_inner.addWidget(self._summary)
        res_inner.addWidget(self._tree, stretch=1)
        res_panel = QFrame()
        res_panel.setObjectName("glassPanel")
        res_panel.setLayout(res_inner)
        res_panel.setGraphicsEffect(panel_drop_shadow(self))

        copy_btn = QPushButton("Copy paths")
        copy_btn.clicked.connect(self._copy_paths)
        save_btn = QPushButton("Save list to .txt…")
        save_btn.clicked.connect(self._save_list)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        actions = QHBoxLayout()
        actions.addWidget(copy_btn)
        actions.addWidget(save_btn)
        actions.addStretch()
        actions.addWidget(close_btn)

        res_outer = QVBoxLayout()
        res_outer.setContentsMargins(20, 20, 20, 20)
        res_outer.setSpacing(14)
        res_outer.addWidget(res_panel, stretch=1)
        res_outer.addLayout(actions)
        results_page.setLayout(res_outer)

        self._stack.addWidget(progress_page)
        self._stack.addWidget(results_page)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)
        self.setLayout(layout)

        self._worker = NoAudioWorker(config)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def paintEvent(self, _event) -> None:
        paint_dark_gradient(self)

    def _on_progress(self, percent: int, message: str) -> None:
        self._bar.setValue(max(0, min(100, percent)))
        self._status.setText(message)

    def _on_finished(self, results) -> None:
        self._results = results or []
        self._populate_results()
        self._stack.setCurrentIndex(1)

    def _on_failed(self, error: str) -> None:
        QMessageBox.critical(self, "Failed", error)
        self.reject()

    def _on_cancel(self) -> None:
        self._worker.request_cancel()
        self._status.setText("Cancelling…")
        self._cancel_btn.setEnabled(False)

    def _populate_results(self) -> None:
        self._tree.clear()
        if not self._results:
            self._summary.setText("No videos without audio were found.")
            return
        total_size = sum(f.size for f in self._results)
        self._summary.setText(
            f"Found {len(self._results)} video(s) without an audio track. "
            f"Total size: {_fmt_size(total_size)}."
        )
        for f in self._results:
            duration = _fmt_duration(f.metadata.duration) if f.metadata else ""
            item = QTreeWidgetItem([str(f.path), _fmt_size(f.size), duration, ""])
            item.setData(0, Qt.ItemDataRole.UserRole, f)
            for col in range(4):
                item.setSizeHint(col, QSize(0, 40))
            item.setIcon(3, folder_icon(28))
            item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(3, "Show in folder")
            self._tree.addTopLevelItem(item)

    def _copy_paths(self) -> None:
        if not self._results:
            return
        QGuiApplication.clipboard().setText("\n".join(str(f.path) for f in self._results))
        QMessageBox.information(self, "Copied", f"{len(self._results)} path(s) copied to clipboard.")

    def _save_list(self) -> None:
        if not self._results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save list", "videos_without_audio.txt", "Text files (*.txt);;All files (*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fp:
                for f in self._results:
                    fp.write(f"{f.path}\n")
        except OSError as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return
        QMessageBox.information(self, "Saved", f"Wrote {len(self._results)} path(s) to {Path(path).name}.")

    def _on_double_click(self, item: QTreeWidgetItem, _column: int) -> None:
        f = item.data(0, Qt.ItemDataRole.UserRole)
        if f is None:
            return
        self._play(f.path)

    def _on_context_menu(self, position) -> None:
        item = self._tree.itemAt(position)
        if item is None:
            return
        f = item.data(0, Qt.ItemDataRole.UserRole)
        if f is None:
            return
        menu = QMenu(self)
        play_action = menu.addAction("Play in default player")
        show_action = menu.addAction("Show in folder")
        chosen = menu.exec(self._tree.viewport().mapToGlobal(position))
        if chosen is play_action:
            self._play(f.path)
        elif chosen is show_action:
            self._show_in_folder(f.path)

    def _on_item_click(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 3:
            return
        f = item.data(0, Qt.ItemDataRole.UserRole)
        if f is not None:
            self._show_in_folder(f.path)

    def _play(self, path) -> None:
        err = open_in_default_player(path)
        if err:
            QMessageBox.warning(self, "Could not open file", err)

    def _show_in_folder(self, path) -> None:
        err = show_in_explorer(path)
        if err:
            QMessageBox.warning(self, "Could not open Explorer", err)

    def closeEvent(self, event) -> None:
        if self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(5000)
        super().closeEvent(event)
