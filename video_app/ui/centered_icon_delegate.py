from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem


class CenteredIconDelegate(QStyledItemDelegate):
    """Paint an item icon centered in its cell, without Qt's default decoration inset."""

    def __init__(self, icon_size: QSize, parent=None) -> None:
        super().__init__(parent)
        self._icon_size = icon_size

    def paint(self, painter, option, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if not isinstance(icon, QIcon):
            icon = opt.icon

        opt.icon = QIcon()
        opt.text = ""
        style = opt.widget.style() if opt.widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        if icon.isNull():
            return

        x = opt.rect.x() + (opt.rect.width() - self._icon_size.width()) // 2
        y = opt.rect.y() + (opt.rect.height() - self._icon_size.height()) // 2
        rect = QRect(x, y, self._icon_size.width(), self._icon_size.height())
        icon.paint(
            painter,
            rect,
            Qt.AlignmentFlag.AlignCenter,
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
