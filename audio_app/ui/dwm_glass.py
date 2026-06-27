"""Windows 11 DWM glass effect for Qt windows.

Applies the Windows compositor backdrop and makes the native caption transparent
so the title bar does not paint as a solid rectangle. Silently no-ops outside
Windows 11 or when system transparency effects are disabled.
"""

import sys

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QWidget
from shiboken6 import isValid

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36
_DWMWA_SYSTEMBACKDROP_TYPE = 38      # Windows 11 22H2+ (build 22621+)
_DWMWA_MICA_EFFECT = 1029            # Windows 11 21H2 (build 22000) fallback

# DWM_SYSTEMBACKDROP_TYPE values
_DWMSBT_TRANSIENTWINDOW = 3          # Acrylic

# DWM color sentinel values. These are DWORDs, not COLORREF colors.
_DWMWA_COLOR_DEFAULT = 0xFFFFFFFF
_DWMWA_COLOR_NONE = 0xFFFFFFFE


def _is_transparency_enabled() -> bool:
    """Return True if Windows transparency effects are enabled."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "EnableTransparency")
        winreg.CloseKey(key)
        return bool(value)
    except Exception:
        return True  # assume on if we cannot read the registry


def apply_glass_to_window(widget: QWidget) -> None:
    """Apply DWM Acrylic + transparent dark title bar to *widget*'s HWND."""
    if sys.platform != "win32":
        return
    hwnd = int(widget.winId()) if widget.winId() else 0
    if not hwnd:
        return
    try:
        import ctypes

        dwmapi = ctypes.windll.dwmapi

        dark = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark),
            ctypes.sizeof(dark),
        )

        # COLOR_NONE lets the native caption stop painting an opaque dark
        # rectangle over the DWM backdrop.
        caption = ctypes.c_uint(_DWMWA_COLOR_NONE)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_CAPTION_COLOR,
            ctypes.byref(caption),
            ctypes.sizeof(caption),
        )

        text = ctypes.c_uint(_DWMWA_COLOR_DEFAULT)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_TEXT_COLOR,
            ctypes.byref(text),
            ctypes.sizeof(text),
        )

        border = ctypes.c_uint(_DWMWA_COLOR_DEFAULT)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_BORDER_COLOR,
            ctypes.byref(border),
            ctypes.sizeof(border),
        )

        backdrop = ctypes.c_int(_DWMSBT_TRANSIENTWINDOW)
        result = dwmapi.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop),
            ctypes.sizeof(backdrop),
        )

        if result != 0:
            # S_OK is 0; fall back to the older Mica flag on Windows 11 21H2.
            mica = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                _DWMWA_MICA_EFFECT,
                ctypes.byref(mica),
                ctypes.sizeof(mica),
            )

    except Exception:
        pass


class DwmGlassFilter(QObject):
    """App-level event filter that applies glass to every top-level window."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Show, QEvent.Type.WinIdChange):
            try:
                is_top_level = (
                    isinstance(obj, QWidget)
                    and isValid(obj)
                    and obj.isTopLevel()
                )
            except RuntimeError:
                is_top_level = False
            if is_top_level:
                # Defer so Windows has finished compositing/updating the HWND.
                QTimer.singleShot(0, lambda w=obj: self._apply(w))
        return False

    def _apply(self, widget: QWidget) -> None:
        try:
            if widget is None or not isValid(widget) or not widget.isTopLevel():
                return
            hwnd = widget.winId()
        except RuntimeError:
            return
        if not hwnd:
            return
        apply_glass_to_window(widget)


def transparency_enabled() -> bool:
    """Public accessor so callers can warn the user if the setting is off."""
    return _is_transparency_enabled()
