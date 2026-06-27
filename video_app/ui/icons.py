from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap


def make_film_reel_icon() -> QIcon:
    """Render the FilmReelLogo widget to a multi-resolution QIcon for window title bars."""
    from video_app.ui.film_reel_logo import FilmReelLogo
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        widget = FilmReelLogo(size)
        widget.ensurePolished()
        pixmap = widget.grab()
        icon.addPixmap(pixmap)
    return icon


def folder_icon(size: int = 28) -> QIcon:
    """Stylized blue folder icon (tab + body), matching the home-screen reference."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)

    s = float(size)
    body_color = QColor(160, 200, 245, 245)
    tab_color = QColor(105, 160, 220, 250)

    tab_radius = s * 0.10
    tab_x = s * 0.10
    tab_y = s * 0.20
    tab_w = s * 0.42
    tab_h = s * 0.20
    p.setBrush(QBrush(tab_color))
    p.drawRoundedRect(QRectF(tab_x, tab_y, tab_w, tab_h), tab_radius, tab_radius)

    body_radius = s * 0.10
    body_x = s * 0.06
    body_y = s * 0.32
    body_w = s * 0.88
    body_h = s * 0.52
    p.setBrush(QBrush(body_color))
    p.drawRoundedRect(QRectF(body_x, body_y, body_w, body_h), body_radius, body_radius)

    p.end()
    return QIcon(pix)
