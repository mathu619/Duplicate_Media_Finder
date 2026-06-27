import json
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from audio_app.core.cache import cache_stats
from audio_app.core.ffmpeg import find_fpcalc
from audio_app.models.scan_config import DetectionTier, ScanConfig, ScanRoot
from audio_app.ui.add_files_dialog import AddFilesDialog
from audio_app.ui.dependencies_dialog import DependenciesDialog
from audio_app.ui.download_dialog import DownloadDialog
from audio_app.ui.file_actions import open_folder_in_explorer, show_in_explorer
from audio_app.ui.cassette_logo import TitleHeader
from audio_app.ui.icons import folder_icon
from audio_app.ui.progress_dialog import ProgressDialog
from audio_app.ui.results_view import ResultsView
from audio_app.ui.theme_helpers import (
    paint_dark_gradient,
    panel_drop_shadow,
    primary_button_glow,
    setup_dark_palette,
)
from audio_app.workers.scan_worker import ScanWorker


def _fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


_FOLDER_ICON = "📁"  # leading marker before path text
_FILE_ICON = "🎵"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mathu's Duplicate Audio Finder")
        self.resize(960, 680)
        setup_dark_palette(self)

        # --- Header ---
        header = TitleHeader()

        # --- Folders / files panel ---
        self._roots_tree = QTreeWidget()
        self._roots_tree.setHeaderLabels(["Folder or file", ""])
        self._roots_tree.setColumnCount(2)
        self._roots_tree.setRootIsDecorated(False)
        self._roots_tree.setIndentation(0)
        self._roots_tree.setUniformRowHeights(True)
        self._roots_tree.setColumnWidth(1, 220)
        self._roots_tree.header().setStretchLastSection(False)
        self._roots_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._roots_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._roots_tree.setFrameShape(QFrame.Shape.NoFrame)
        self._roots_tree.setStyleSheet("QTreeWidget { background: transparent; border: none; }")

        section_label = QLabel("FOLDERS & FILES TO SCAN")
        section_label.setObjectName("sectionLabel")

        folders_panel_layout = QVBoxLayout()
        folders_panel_layout.setContentsMargins(16, 14, 16, 14)
        folders_panel_layout.setSpacing(10)
        folders_panel_layout.addWidget(section_label)
        folders_panel_layout.addWidget(self._roots_tree, stretch=1)

        self._folders_panel = QFrame()
        self._folders_panel.setObjectName("glassPanel")
        self._folders_panel.setLayout(folders_panel_layout)

        # --- Action buttons row ---
        add_folder_btn = QPushButton("+ Add Folder")
        add_folder_btn.clicked.connect(self._on_add_folder)

        add_files_btn = QPushButton("+ Add Files")
        add_files_btn.clicked.connect(self._on_add_files)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._on_remove_selected)

        action_buttons = QHBoxLayout()
        action_buttons.addWidget(add_folder_btn)
        action_buttons.addWidget(add_files_btn)
        action_buttons.addWidget(remove_btn)
        action_buttons.addStretch()

        # --- Bottom panel (tier + start) ---
        self._tier_combo = QComboBox()
        for tier in DetectionTier:
            self._tier_combo.addItem(tier.label, tier)

        detection_label = QLabel("Detection level")
        detection_label.setObjectName("detectionLabel")

        self._start_btn = QPushButton("Start Scan")
        self._start_btn.setObjectName("primaryButton")
        self._start_btn.clicked.connect(self._on_start_scan)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(14, 10, 14, 10)
        bottom_row.setSpacing(10)
        bottom_row.addWidget(detection_label)
        bottom_row.addWidget(self._tier_combo, stretch=1)
        bottom_row.addWidget(self._start_btn)

        self._bottom_panel = QFrame()
        self._bottom_panel.setObjectName("glassPanel")
        self._bottom_panel.setLayout(bottom_row)

        # --- Compose ---
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(header)
        layout.addWidget(self._folders_panel, stretch=1)
        layout.addLayout(action_buttons)
        layout.addWidget(self._bottom_panel)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._apply_drop_shadows()
        self._build_menu()
        self._build_status_bar()
        self._restore_session()

    # ---------- visual effects ----------

    def paintEvent(self, _event) -> None:
        paint_dark_gradient(self)

    def _apply_drop_shadows(self) -> None:
        for panel in (self._folders_panel, self._bottom_panel):
            panel.setGraphicsEffect(panel_drop_shadow(self))
        self._start_btn.setGraphicsEffect(primary_button_glow(self))

    # ---------- menu + status bar ----------

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction("Manage dependencies...", self._on_manage_deps)

    def _build_status_bar(self) -> None:
        self._cache_label = QLabel()
        self.statusBar().addPermanentWidget(self._cache_label)
        self._refresh_cache_label()

    def _refresh_cache_label(self) -> None:
        s = cache_stats()
        self._cache_label.setText(
            f"Cache: {s['audio_files']:,} audio files - {_fmt_size(s['size_bytes'])}"
        )

    # ---------- list management ----------

    def _on_add_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select folder to scan")
        if not path:
            return
        if self._find_item_by_path(path) is not None:
            return
        self._append_folder_item(path, recursive=True)

    def _on_add_files(self) -> None:
        dlg = AddFilesDialog(parent=self)
        if dlg.exec() != AddFilesDialog.DialogCode.Accepted:
            return
        added = 0
        for p in dlg.paths:
            if self._find_item_by_path(p) is not None:
                continue
            self._append_file_item(p)
            added += 1
        if added:
            self.statusBar().showMessage(f"Added {added} file(s).", 6000)

    def _on_remove_selected(self) -> None:
        item = self._roots_tree.currentItem()
        if item is None:
            return
        idx = self._roots_tree.indexOfTopLevelItem(item)
        if idx >= 0:
            self._roots_tree.takeTopLevelItem(idx)

    def _append_folder_item(self, path: str, recursive: bool) -> None:
        display = f"{_FOLDER_ICON}   {path}"
        item = QTreeWidgetItem([display, ""])
        item.setSizeHint(0, QSize(0, 40))
        item.setSizeHint(1, QSize(220, 40))
        item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "folder", "path": path, "recursive": recursive})
        self._roots_tree.addTopLevelItem(item)
        self._attach_actions(item, path, kind="folder", recursive=recursive)

    def _append_file_item(self, path: str) -> None:
        display = f"{_FILE_ICON}   {path}"
        item = QTreeWidgetItem([display, ""])
        item.setSizeHint(0, QSize(0, 40))
        item.setSizeHint(1, QSize(220, 40))
        item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "file", "path": path})
        self._roots_tree.addTopLevelItem(item)
        self._attach_actions(item, path, kind="file")

    def _attach_actions(
        self, item: QTreeWidgetItem, path: str, kind: str, recursive: bool = True
    ) -> None:
        container = QWidget()
        container.setFixedHeight(40)
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 10, 10)
        h.setSpacing(10)
        h.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        h.addStretch()

        if kind == "folder":
            cb = QCheckBox("Exclude Subfolders")
            cb.setFixedHeight(24)
            cb.setToolTip("If checked, only files in this folder are scanned (no subfolders)")
            cb.setChecked(not recursive)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.toggled.connect(
                lambda checked, it=item: self._on_recursive_toggled(it, not checked)
            )
            h.addWidget(cb, alignment=Qt.AlignmentFlag.AlignVCenter)

            divider = QFrame()
            divider.setObjectName("actionDivider")
            divider.setFixedSize(QSize(1, 20))
            h.addWidget(divider, alignment=Qt.AlignmentFlag.AlignVCenter)

        btn = QToolButton()
        btn.setIcon(folder_icon(28))
        btn.setIconSize(QSize(26, 26))
        btn.setFixedSize(QSize(30, 30))
        btn.setToolTip("Show in folder")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if kind == "folder":
            btn.clicked.connect(lambda _checked=False, p=path: self._open_folder(p))
        else:
            btn.clicked.connect(lambda _checked=False, p=path: self._show_file(p))
        h.addWidget(btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        container.setMinimumHeight(40)
        container.setLayout(h)
        self._roots_tree.setItemWidget(item, 1, container)

    def _on_recursive_toggled(self, item: QTreeWidgetItem, recursive: bool) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        data["recursive"] = recursive
        item.setData(0, Qt.ItemDataRole.UserRole, data)

    def _open_folder(self, path: str) -> None:
        err = open_folder_in_explorer(Path(path))
        if err:
            QMessageBox.warning(self, "Could not open folder", err)

    def _show_file(self, path: str) -> None:
        err = show_in_explorer(Path(path))
        if err:
            QMessageBox.warning(self, "Could not open Explorer", err)

    def _find_item_by_path(self, path: str) -> QTreeWidgetItem | None:
        target = path.lower()
        for i in range(self._roots_tree.topLevelItemCount()):
            it = self._roots_tree.topLevelItem(i)
            data = it.data(0, Qt.ItemDataRole.UserRole) or {}
            if str(data.get("path", "")).lower() == target:
                return it
        return None

    # ---------- collect + scan ----------

    def _collect_config(self) -> ScanConfig | None:
        roots: list[ScanRoot] = []
        extras: list[str] = []
        for i in range(self._roots_tree.topLevelItemCount()):
            it = self._roots_tree.topLevelItem(i)
            data = it.data(0, Qt.ItemDataRole.UserRole) or {}
            kind = data.get("kind")
            path = data.get("path", "")
            if kind == "folder":
                roots.append(ScanRoot(path=path, recursive=bool(data.get("recursive", True))))
            elif kind == "file":
                extras.append(path)
        if not roots and not extras:
            QMessageBox.information(
                self, "Nothing to scan", "Add at least one folder or file."
            )
            return None
        tier = self._tier_combo.currentData()
        return ScanConfig(roots=roots, tier=tier, extra_files=extras)

    def _on_start_scan(self) -> None:
        config = self._collect_config()
        if config is None:
            return
        if not self._ensure_binaries_for_tier(config.tier):
            return
        self._save_session()
        worker = ScanWorker(config)
        dialog = ProgressDialog(worker, parent=self)
        dialog.exec()
        if dialog.cancelled:
            self.statusBar().showMessage("Scan cancelled.", 6000)
            return
        if dialog.error is not None:
            QMessageBox.critical(self, "Scan failed", dialog.error)
            return
        self._show_scan_stats(worker)
        self._refresh_cache_label()
        groups = dialog.groups
        if not groups:
            QMessageBox.information(
                self, "No duplicates found", "No duplicate audio files were found in the selected folders."
            )
            return
        ResultsView(groups, parent=self).exec()

    def _show_scan_stats(self, worker: ScanWorker) -> None:
        elapsed = worker.elapsed_seconds
        if elapsed >= 60:
            mins, secs = divmod(int(elapsed), 60)
            elapsed_str = f"{mins}m {secs}s"
        else:
            elapsed_str = f"{elapsed:.1f}s"
        self.statusBar().showMessage(
            f"Last scan: {worker.cache_hits:,} from cache, "
            f"{worker.cache_computes:,} computed in {elapsed_str}",
            15000,
        )

    def _ensure_binaries_for_tier(self, tier: DetectionTier) -> bool:
        needs_fpcalc = tier in (
            DetectionTier.DEEP_FAST,
            DetectionTier.CONTAINED_CLIPS,
        )

        if needs_fpcalc and find_fpcalc() is None:
            if not self._offer_download(
                "chromaprint", "Chromaprint", "~3 MB",
                "Chromaprint (fpcalc) is required for this detection level.",
            ):
                return False
        return True

    def _offer_download(self, target: str, friendly: str, size: str, reason: str) -> bool:
        confirm = QMessageBox.question(
            self,
            f"Download {friendly}?",
            f"{reason}\n\nDownload it now? ({size})",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return False
        dlg = DownloadDialog(target, friendly, parent=self)
        dlg.exec()
        return dlg.succeeded

    def _on_manage_deps(self) -> None:
        DependenciesDialog(parent=self).exec()

    # ---------- session persistence ----------

    def _settings(self) -> QSettings:
        return QSettings("Mathu", "DuplicateAudioFinder")

    def _restore_session(self) -> None:
        s = self._settings()
        geom = s.value("mainwindow/geometry")
        if geom:
            self.restoreGeometry(geom)
        state = s.value("mainwindow/state")
        if state:
            self.restoreState(state)

        tier_name = s.value("scan/tier")
        if isinstance(tier_name, str):
            for i in range(self._tier_combo.count()):
                if self._tier_combo.itemData(i).name == tier_name:
                    self._tier_combo.setCurrentIndex(i)
                    break

        roots_json = s.value("scan/roots")
        if isinstance(roots_json, str):
            try:
                entries = json.loads(roots_json)
            except json.JSONDecodeError:
                entries = []
            for entry in entries:
                path = entry.get("path", "")
                if not path:
                    continue
                kind = entry.get("kind", "folder")
                if kind == "folder":
                    if not Path(path).is_dir():
                        continue
                    self._append_folder_item(path, recursive=bool(entry.get("recursive", True)))
                elif kind == "file":
                    if not Path(path).is_file():
                        continue
                    self._append_file_item(path)

    def _save_session(self) -> None:
        s = self._settings()
        s.setValue("mainwindow/geometry", self.saveGeometry())
        s.setValue("mainwindow/state", self.saveState())
        tier = self._tier_combo.currentData()
        if tier is not None:
            s.setValue("scan/tier", tier.name)
        entries: list[dict] = []
        for i in range(self._roots_tree.topLevelItemCount()):
            it = self._roots_tree.topLevelItem(i)
            data = it.data(0, Qt.ItemDataRole.UserRole) or {}
            kind = data.get("kind")
            if kind == "folder":
                entries.append({
                    "kind": "folder",
                    "path": data.get("path", ""),
                    "recursive": bool(data.get("recursive", True)),
                })
            elif kind == "file":
                entries.append({"kind": "file", "path": data.get("path", "")})
        s.setValue("scan/roots", json.dumps(entries))

    def closeEvent(self, event) -> None:
        self._save_session()
        super().closeEvent(event)
