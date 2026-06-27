from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from audio_app.ui.icons import make_cassette_icon
from video_app.ui.icons import make_film_reel_icon
from video_app.ui.theme_helpers import paint_dark_gradient, panel_drop_shadow


class SelectionWindow(QMainWindow):
    media_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mathu's Duplicate Media Finder")
        self.resize(960, 620)

        title = QLabel("Which duplicates do you want to find?")
        title.setObjectName("chooserTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Segoe UI")
        title_font.setPointSize(34)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)

        video_button = self._choice_button("Video Files", "video", make_film_reel_icon())
        audio_button = self._choice_button("Audio Files", "audio", make_cassette_icon())

        choices = QHBoxLayout()
        choices.setSpacing(18)
        choices.addWidget(video_button)
        choices.addWidget(audio_button)

        panel = QFrame()
        panel.setObjectName("chooserPanel")
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(18, 18, 18, 18)
        panel_layout.setSpacing(18)
        panel_layout.addLayout(choices)
        panel.setLayout(panel_layout)
        panel.setGraphicsEffect(panel_drop_shadow(self))

        layout = QVBoxLayout()
        layout.setContentsMargins(34, 34, 34, 34)
        layout.setSpacing(24)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(panel, stretch=3)
        layout.addStretch(1)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def paintEvent(self, _event) -> None:
        paint_dark_gradient(self)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        if event.isAccepted():
            app = QApplication.instance()
            if app is not None:
                app.quit()

    def _choice_button(self, label: str, media: str, icon) -> QToolButton:
        button = QToolButton()
        button.setObjectName(f"{media}Choice")
        button.setText(label)
        button.setIcon(icon)
        button.setIconSize(QSize(128, 128))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        button.setMinimumSize(QSize(320, 300))
        font = QFont("Segoe UI")
        font.setPointSize(27)
        font.setWeight(QFont.Weight.DemiBold)
        button.setFont(font)
        button.clicked.connect(lambda: self.media_selected.emit(media))
        return button
