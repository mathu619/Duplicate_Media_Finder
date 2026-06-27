from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from video_app.core.deleter import send_to_recycle_bin
from video_app.core.quality import pick_best_index
from video_app.models.duplicate_group import DuplicateGroup, DuplicateKind
from video_app.ui.centered_icon_delegate import CenteredIconDelegate
from video_app.ui.file_actions import (
    open_in_default_player,
    show_in_explorer,
)
from video_app.ui.icons import folder_icon
from video_app.ui.theme_helpers import (
    paint_dark_gradient,
    panel_drop_shadow,
    primary_button_glow,
    setup_dark_palette,
)


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


def _fmt_bitrate(bps: int) -> str:
    if bps <= 0:
        return ""
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.1f} Mbps"
    return f"{bps / 1000:.0f} kbps"


class ResultsView(QDialog):
    def __init__(self, groups: list[DuplicateGroup], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Duplicate Video Finder — Results")
        self.resize(1180, 700)
        setup_dark_palette(self)

        self._groups = list(groups)
        self._has_metadata = any(
            f.metadata is not None for g in self._groups for f in g.files
        )

        title = QLabel("DUPLICATES FOUND")
        title.setObjectName("sectionLabel")
        self._summary = QLabel()

        self._tree = QTreeWidget()
        if self._has_metadata:
            self._tree.setHeaderLabels(
                ["File", "Size", "Duration", "Resolution", "Bitrate", "Codec", ""]
            )
            self._action_col = 6
            fixed_widths = {1: 80, 2: 80, 3: 100, 4: 90, 5: 80, 6: 44}
        else:
            self._tree.setHeaderLabels(["File", "Size", ""])
            self._action_col = 2
            fixed_widths = {1: 90, 2: 44}
        header = self._tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in fixed_widths:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        for col, w in fixed_widths.items():
            self._tree.setColumnWidth(col, w)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemClicked.connect(self._on_item_click)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.setIconSize(QSize(26, 26))
        self._tree.setItemDelegateForColumn(
            self._action_col, CenteredIconDelegate(QSize(26, 26), self._tree)
        )
        self._tree.setIndentation(14)
        self._tree.setRootIsDecorated(False)
        self._tree.setFrameShape(QFrame.Shape.NoFrame)
        self._tree.setStyleSheet("QTreeWidget { background: transparent; border: none; }")

        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(16, 14, 16, 14)
        panel_layout.setSpacing(10)
        panel_layout.addWidget(title)
        panel_layout.addWidget(self._summary)
        panel_layout.addWidget(self._tree, stretch=1)

        self._panel = QFrame()
        self._panel.setObjectName("glassPanel")
        self._panel.setLayout(panel_layout)
        self._panel.setGraphicsEffect(panel_drop_shadow(self))

        keep_best_btn = QPushButton("Keep best quality per group")
        keep_best_btn.clicked.connect(self._keep_best_in_each)

        check_all_btn = QPushButton("Mark every file")
        check_all_btn.clicked.connect(self._mark_all)

        uncheck_all_btn = QPushButton("Unmark all")
        uncheck_all_btn.clicked.connect(self._uncheck_all)

        delete_btn = QPushButton("Send checked to Recycle Bin")
        delete_btn.setObjectName("primaryButton")
        delete_btn.clicked.connect(self._on_delete)
        delete_btn.setGraphicsEffect(primary_button_glow(self))

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        top = QHBoxLayout()
        top.addWidget(keep_best_btn)
        top.addWidget(check_all_btn)
        top.addWidget(uncheck_all_btn)
        top.addStretch()

        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(delete_btn)
        bottom.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(top)
        layout.addWidget(self._panel, stretch=1)
        layout.addLayout(bottom)
        self.setLayout(layout)

        self._populate()

    def paintEvent(self, _event) -> None:
        paint_dark_gradient(self)

    def _populate(self) -> None:
        self._tree.clear()
        total_wasted = sum(g.wasted_space for g in self._groups)
        self._summary.setText(
            f"{len(self._groups)} duplicate group(s). "
            f"Potential savings if one file kept per group: {_fmt_size(total_wasted)}."
        )
        column_count = self._action_col + 1
        for i, group in enumerate(self._groups, start=1):
            is_clip = group.kind is DuplicateKind.CONTAINED_CLIP
            # SAME_CONTENT: keeper is the best-quality file; mark the rest.
            # CONTAINED_CLIP: by convention files[0] is the shorter clip; mark it only.
            keeper = 1 if is_clip and len(group.files) > 1 else pick_best_index(group.files)
            header_cols = [""] * column_count
            header_cols[0] = (
                f"Group {i} — {len(group.files)} files — "
                f"{_fmt_size(group.wasted_space)} recoverable — {group.reason}"
            )
            header = QTreeWidgetItem(header_cols)
            for col in range(column_count):
                header.setSizeHint(col, QSize(0, 40))
            header.setFlags(header.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._tree.addTopLevelItem(header)
            for j, f in enumerate(group.files):
                if is_clip:
                    tag = "   (shorter clip)" if j == 0 else "   (contains the clip)"
                    checked = (j == 0)
                else:
                    tag = "   (best quality)" if j == keeper else ""
                    checked = (j != keeper)
                row = [str(f.path) + tag, _fmt_size(f.size)]
                if self._has_metadata:
                    m = f.metadata
                    row.extend(
                        [
                            _fmt_duration(m.duration) if m else "",
                            m.resolution if m else "",
                            _fmt_bitrate(m.bitrate) if m else "",
                            m.video_codec if m else "",
                        ]
                    )
                row.append("")  # action column placeholder
                child = QTreeWidgetItem(row)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(
                    0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )
                child.setData(0, Qt.ItemDataRole.UserRole, f)
                for col in range(column_count):
                    child.setSizeHint(col, QSize(0, 40))
                child.setIcon(self._action_col, folder_icon(28))
                child.setTextAlignment(
                    self._action_col, Qt.AlignmentFlag.AlignCenter
                )
                child.setToolTip(self._action_col, "Show in folder")
                header.addChild(child)
            header.setExpanded(True)

    def _iter_children(self):
        for i in range(self._tree.topLevelItemCount()):
            header = self._tree.topLevelItem(i)
            for j in range(header.childCount()):
                yield header, j, header.child(j)

    def _keep_best_in_each(self) -> None:
        for i in range(self._tree.topLevelItemCount()):
            header = self._tree.topLevelItem(i)
            group = self._groups[i]
            if group.kind is DuplicateKind.CONTAINED_CLIP:
                # For contained clips, mark the clip (files[0]) only.
                for j in range(header.childCount()):
                    header.child(j).setCheckState(
                        0, Qt.CheckState.Checked if j == 0 else Qt.CheckState.Unchecked
                    )
                continue
            keeper = pick_best_index(group.files)
            for j in range(header.childCount()):
                header.child(j).setCheckState(
                    0, Qt.CheckState.Unchecked if j == keeper else Qt.CheckState.Checked
                )

    def _mark_all(self) -> None:
        for _, _, child in self._iter_children():
            child.setCheckState(0, Qt.CheckState.Checked)

    def _uncheck_all(self) -> None:
        for _, _, child in self._iter_children():
            child.setCheckState(0, Qt.CheckState.Unchecked)

    def _collect_checked(self) -> tuple[list[Path], list[int]]:
        """Returns (paths to delete, indices of groups where every file was checked)."""
        paths: list[Path] = []
        all_checked_groups: list[int] = []
        for i in range(self._tree.topLevelItemCount()):
            header = self._tree.topLevelItem(i)
            checked = [
                header.child(j) for j in range(header.childCount())
                if header.child(j).checkState(0) == Qt.CheckState.Checked
            ]
            if checked and len(checked) == header.childCount():
                all_checked_groups.append(i + 1)
                continue
            paths.extend(item.data(0, Qt.ItemDataRole.UserRole).path for item in checked)
        return paths, all_checked_groups

    def _on_delete(self) -> None:
        paths, all_checked = self._collect_checked()
        if all_checked:
            QMessageBox.warning(
                self,
                "Keep at least one per group",
                f"You marked every file in group(s) {', '.join(map(str, all_checked))}. "
                "Uncheck the one you want to keep in each group, then try again.",
            )
            return
        if not paths:
            QMessageBox.information(self, "Nothing to delete", "No files are marked.")
            return
        confirm = QMessageBox.question(
            self,
            "Send to Recycle Bin",
            f"Send {len(paths)} file(s) to the Recycle Bin?\nYou can restore them from there if needed.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, failed = send_to_recycle_bin(paths)

        ok_set = {str(p) for p in ok}
        new_groups: list[DuplicateGroup] = []
        for g in self._groups:
            remaining = [f for f in g.files if str(f.path) not in ok_set]
            if len(remaining) > 1:
                new_groups.append(
                    DuplicateGroup(files=remaining, reason=g.reason, kind=g.kind)
                )
        self._groups = new_groups
        self._populate()

        msg = f"Moved {len(ok)} file(s) to Recycle Bin."
        if failed:
            sample = "\n".join(f"{p}: {r}" for p, r in failed[:5])
            more = f"\n…and {len(failed) - 5} more" if len(failed) > 5 else ""
            msg += f"\n\nFailed: {len(failed)}\n{sample}{more}"
        QMessageBox.information(self, "Done", msg)

    def _on_context_menu(self, position) -> None:
        item = self._tree.itemAt(position)
        if item is None or item.parent() is None:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole).path
        menu = QMenu(self)
        play_action = menu.addAction("Play in default player")
        show_action = menu.addAction("Show in folder")
        chosen = menu.exec(self._tree.viewport().mapToGlobal(position))
        if chosen is play_action:
            self._play(path)
        elif chosen is show_action:
            self._show_in_folder(path)

    def _on_item_click(self, item: QTreeWidgetItem, column: int) -> None:
        if column != self._action_col or item.parent() is None:
            return
        self._show_in_folder(item.data(0, Qt.ItemDataRole.UserRole).path)

    def _on_double_click(self, item: QTreeWidgetItem, _column: int) -> None:
        if item.parent() is None:
            return
        self._play(item.data(0, Qt.ItemDataRole.UserRole).path)

    def _play(self, path: Path) -> None:
        err = open_in_default_player(path)
        if err:
            QMessageBox.warning(self, "Could not open file", err)

    def _show_in_folder(self, path: Path) -> None:
        err = show_in_explorer(path)
        if err:
            QMessageBox.warning(self, "Could not open Explorer", err)
