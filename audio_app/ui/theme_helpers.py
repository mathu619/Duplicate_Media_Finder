from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPalette
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def setup_dark_palette(widget: QWidget) -> None:
    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0f0c1a"))
    widget.setPalette(palette)


def paint_dark_gradient(widget: QWidget) -> None:
    painter = QPainter(widget)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, widget.width(), widget.height())
    gradient.setColorAt(0.0, QColor("#0f0c1a"))
    gradient.setColorAt(0.45, QColor("#13102a"))
    gradient.setColorAt(1.0, QColor("#0c1520"))
    painter.fillRect(widget.rect(), gradient)


def panel_drop_shadow(parent: QWidget) -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect(parent)
    shadow.setColor(QColor(0, 0, 0, 180))
    shadow.setBlurRadius(32)
    shadow.setOffset(0, 8)
    return shadow


def primary_button_glow(parent: QWidget) -> QGraphicsDropShadowEffect:
    glow = QGraphicsDropShadowEffect(parent)
    glow.setColor(QColor(100, 80, 255, 160))
    glow.setBlurRadius(20)
    glow.setOffset(0, 4)
    return glow
