import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class FilmReelLogo(QWidget):
    """Stylized classic film reel with film strip unrolling out the bottom-right."""

    def __init__(self, size: int = 48, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = float(self.width())
        cx, cy = s / 2.0, s / 2.0

        accent = QColor(160, 110, 255, 235)
        accent_dim = QColor(120, 80, 255, 200)
        film_dark = QColor(40, 30, 70, 230)
        film_light = QColor(200, 180, 255, 220)

        outer = s * 0.40
        hub = s * 0.07
        hole_r = s * 0.055
        hole_d = s * 0.255

        # Film strip unrolling out (drawn first so reel sits on top)
        strip = QPainterPath()
        strip.moveTo(cx + s * 0.30, cy + s * 0.10)
        strip.cubicTo(
            cx + s * 0.55, cy + s * 0.22,
            cx + s * 0.45, cy + s * 0.42,
            cx + s * 0.05, cy + s * 0.46,
        )
        p.setPen(QPen(film_dark, s * 0.10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(strip)
        # Film perforations along the strip
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(film_light))
        for t in (0.25, 0.5, 0.75):
            pt = strip.pointAtPercent(t)
            p.drawRoundedRect(
                QRectF(pt.x() - s * 0.018, pt.y() - s * 0.014, s * 0.036, s * 0.028),
                s * 0.005, s * 0.005,
            )

        # Reel outer ring
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(accent, max(1.5, s * 0.045), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(QPointF(cx, cy), outer, outer)

        # Spokes (lines from hub to each hole)
        p.setPen(QPen(accent_dim, max(1.0, s * 0.020), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for i in range(6):
            angle = math.radians(i * 60.0 + 30.0)
            hx = cx + math.cos(angle) * hole_d
            hy = cy + math.sin(angle) * hole_d
            p.drawLine(QPointF(cx, cy), QPointF(hx, hy))

        # Spoke holes
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(accent))
        for i in range(6):
            angle = math.radians(i * 60.0 + 30.0)
            hx = cx + math.cos(angle) * hole_d
            hy = cy + math.sin(angle) * hole_d
            p.drawEllipse(QPointF(hx, hy), hole_r, hole_r)

        # Center hub
        p.setBrush(QBrush(QColor(255, 255, 255, 240)))
        p.drawEllipse(QPointF(cx, cy), hub, hub)


class TitleHeader(QWidget):
    """Header strip with film-reel logo + 'Mathu's True Duplicate Video Finder' title."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

        self._logo = FilmReelLogo(size=52, parent=self)

        title = QLabel("Mathu's True Duplicate Video Finder")
        title.setStyleSheet(
            "color: #ffffff;"
            "font-family: 'Inter';"
            "font-size: 22px;"
            "font-weight: 700;"
            "letter-spacing: -0.01em;"
            "background: transparent;"
        )

        subtitle = QLabel("Find duplicates by content, Not just by metadata.")
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
