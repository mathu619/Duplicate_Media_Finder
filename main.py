import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMainWindow

from media_finder.icons import make_media_icon
from media_finder.selection_window import SelectionWindow
from video_app.ui.dwm_glass import DwmGlassFilter

_APP_NAME = "Mathu's Duplicate Media Finder"
_ORG_NAME = "Mathu"


def _load_inter_fonts() -> bool:
    resources = Path(__file__).resolve().parent / "resources"
    loaded_any = False
    for name in ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf"):
        path = resources / name
        if path.exists() and QFontDatabase.addApplicationFont(str(path)) != -1:
            loaded_any = True
    return loaded_any


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_stylesheet() -> str:
    root = Path(__file__).resolve().parent
    theme = _read_text(root / "video_app" / "ui" / "theme.qss")
    chooser = _read_text(root / "media_finder" / "selector.qss")
    return "\n\n".join(part for part in (theme, chooser) if part)


def _create_flow_window(media: str) -> QMainWindow:
    if media == "video":
        from video_app.ui.main_window import MainWindow

        return MainWindow()
    if media == "audio":
        from audio_app.ui.main_window import MainWindow

        return MainWindow()
    raise ValueError(f"Unknown media type: {media}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(_APP_NAME)
    app.setOrganizationName(_ORG_NAME)
    app.setQuitOnLastWindowClosed(False)

    if _load_inter_fonts():
        app.setFont(QFont("Inter", 10))

    qss = _load_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    app.setWindowIcon(make_media_icon())

    glass = DwmGlassFilter(app)
    app.installEventFilter(glass)

    selector = SelectionWindow()
    active_window: dict[str, QMainWindow | None] = {"window": None}

    def show_selector() -> None:
        active_window["window"] = None
        selector.show()
        selector.raise_()
        selector.activateWindow()

    def open_flow(media: str) -> None:
        selector.hide()
        window = _create_flow_window(media)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        media_menu = window.menuBar().addMenu("&Media")
        choose_action = media_menu.addAction("Choose media type")
        choose_action.triggered.connect(window.close)
        window.destroyed.connect(lambda _obj=None: show_selector())
        active_window["window"] = window
        window.show()

    selector.media_selected.connect(open_flow)
    selector.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

