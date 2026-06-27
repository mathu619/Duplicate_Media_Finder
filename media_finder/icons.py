from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _pixmap(size: int) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    return pix


def make_media_icon(size: int = 256) -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_draw_media_mark(s))
    return icon if size == 256 else QIcon(_draw_media_mark(size))


def make_video_choice_icon(size: int = 128) -> QIcon:
    return QIcon(_draw_video_mark(size))


def make_audio_choice_icon(size: int = 128) -> QIcon:
    return QIcon(_draw_audio_mark(size))


def _draw_media_mark(size: int) -> QPixmap:
    pix = _pixmap(size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(28, 22, 46))
    p.drawRoundedRect(QRectF(s * 0.08, s * 0.08, s * 0.84, s * 0.84), s * 0.18, s * 0.18)

    p.setPen(QPen(QColor(104, 190, 255), max(2, int(s * 0.055)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(s * 0.28, s * 0.32), QPointF(s * 0.28, s * 0.68))
    p.drawLine(QPointF(s * 0.72, s * 0.32), QPointF(s * 0.72, s * 0.68))

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(144, 92, 255))
    play = QPainterPath()
    play.moveTo(s * 0.40, s * 0.32)
    play.lineTo(s * 0.40, s * 0.68)
    play.lineTo(s * 0.67, s * 0.50)
    play.closeSubpath()
    p.drawPath(play)

    p.setBrush(QColor(255, 115, 195))
    p.drawEllipse(QRectF(s * 0.58, s * 0.60, s * 0.18, s * 0.18))
    p.setPen(QPen(QColor(255, 115, 195), max(2, int(s * 0.045)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(s * 0.73, s * 0.67), QPointF(s * 0.73, s * 0.30))
    p.drawLine(QPointF(s * 0.73, s * 0.30), QPointF(s * 0.83, s * 0.35))
    p.end()
    return pix


def _draw_video_mark(size: int) -> QPixmap:
    pix = _pixmap(size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)

    p.setPen(QPen(QColor(110, 205, 255), max(2, int(s * 0.035))))
    p.setBrush(QColor(24, 31, 55))
    p.drawRoundedRect(QRectF(s * 0.12, s * 0.20, s * 0.76, s * 0.58), s * 0.08, s * 0.08)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(124, 95, 255))
    play = QPainterPath()
    play.moveTo(s * 0.43, s * 0.36)
    play.lineTo(s * 0.43, s * 0.64)
    play.lineTo(s * 0.65, s * 0.50)
    play.closeSubpath()
    p.drawPath(play)

    p.setBrush(QColor(110, 205, 255))
    for x in (0.22, 0.34, 0.46, 0.58, 0.70):
        p.drawRoundedRect(QRectF(s * x, s * 0.23, s * 0.055, s * 0.09), s * 0.015, s * 0.015)
        p.drawRoundedRect(QRectF(s * x, s * 0.68, s * 0.055, s * 0.07), s * 0.015, s * 0.015)
    p.end()
    return pix


def _draw_audio_mark(size: int) -> QPixmap:
    pix = _pixmap(size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)

    p.setPen(QPen(QColor(255, 125, 200), max(2, int(s * 0.04)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(s * 0.18, s * 0.18, s * 0.64, s * 0.64), s * 0.12, s * 0.12)

    p.setPen(QPen(QColor(255, 125, 200), max(3, int(s * 0.055)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(s * 0.60, s * 0.25), QPointF(s * 0.60, s * 0.62))
    p.drawLine(QPointF(s * 0.60, s * 0.25), QPointF(s * 0.74, s * 0.31))
    p.drawEllipse(QRectF(s * 0.38, s * 0.58, s * 0.22, s * 0.15))

    p.setPen(QPen(QColor(115, 205, 255), max(2, int(s * 0.025)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for i, height in enumerate((0.16, 0.26, 0.36, 0.26, 0.16)):
        x = s * (0.25 + i * 0.08)
        p.drawLine(QPointF(x, s * (0.50 - height / 2)), QPointF(x, s * (0.50 + height / 2)))
    p.end()
    return pix

