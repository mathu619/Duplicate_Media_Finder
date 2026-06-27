import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class CassetteLogo(QWidget):
    """Retro audio cassette logo used in the header and app icon."""

    def __init__(self, size: int = 48, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = float(self.width())

        purple = QColor(160, 110, 255, 235)
        blue = QColor(80, 160, 255, 225)
        ink = QColor(20, 16, 36, 238)
        panel = QColor(245, 238, 255, 232)
        tape = QColor(68, 48, 110, 238)

        body = QRectF(s * 0.08, s * 0.16, s * 0.84, s * 0.62)
        grad = QLinearGradient(body.topLeft(), body.bottomRight())
        grad.setColorAt(0.0, purple)
        grad.setColorAt(1.0, blue)

        p.setPen(QPen(QColor(255, 255, 255, 140), max(1.0, s * 0.025)))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(body, s * 0.09, s * 0.09)

        label = QRectF(s * 0.18, s * 0.24, s * 0.64, s * 0.16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(panel))
        p.drawRoundedRect(label, s * 0.025, s * 0.025)

        window = QRectF(s * 0.20, s * 0.43, s * 0.60, s * 0.20)
        p.setBrush(QBrush(ink))
        p.drawRoundedRect(window, s * 0.045, s * 0.045)

        reel_r = s * 0.095
        hole_r = s * 0.024
        left = QPointF(s * 0.36, s * 0.53)
        right = QPointF(s * 0.64, s * 0.53)

        p.setBrush(QBrush(panel))
        for center in (left, right):
            p.drawEllipse(center, reel_r, reel_r)
            p.setBrush(QBrush(tape))
            for i in range(6):
                angle = math.radians(i * 60)
                pt = QPointF(
                    center.x() + math.cos(angle) * reel_r * 0.48,
                    center.y() + math.sin(angle) * reel_r * 0.48,
                )
                p.drawEllipse(pt, hole_r, hole_r)
            p.setBrush(QBrush(panel))

        p.setPen(QPen(tape, max(1.2, s * 0.030), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(left, right)

        cutout = QPainterPath()
        cutout.moveTo(s * 0.26, s * 0.78)
        cutout.lineTo(s * 0.74, s * 0.78)
        cutout.lineTo(s * 0.66, s * 0.66)
        cutout.lineTo(s * 0.34, s * 0.66)
        cutout.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(15, 12, 30, 230)))
        p.drawPath(cutout)

        p.setPen(QPen(QColor(255, 255, 255, 160), max(1.0, s * 0.020)))
        p.drawLine(QPointF(s * 0.25, s * 0.31), QPointF(s * 0.75, s * 0.31))


class TitleHeader(QWidget):
    """Header strip with cassette logo and app title."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

        self._logo = CassetteLogo(size=52, parent=self)

        title = QLabel("Mathu's Duplicate Audio Finder")
        title.setStyleSheet(
            "color: #ffffff;"
            "font-family: 'Inter';"
            "font-size: 22px;"
            "font-weight: 700;"
            "letter-spacing: 0;"
            "background: transparent;"
        )

        subtitle = QLabel("Find duplicate audio by content, not just metadata.")
        subtitle.setStyleSheet(
            "color: #9070cc;"
            "font-family: 'Inter';"
            "font-size: 12px;"
            "font-weight: 500;"
            "letter-spacing: 0.04em;"
            "background: transparent;"
        )

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        text_col.addWidget(title)
        text_col.addWidget(subtitle)

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 8)
        layout.setSpacing(14)
        layout.addWidget(self._logo)
        layout.addLayout(text_col, stretch=1)
        self.setLayout(layout)
