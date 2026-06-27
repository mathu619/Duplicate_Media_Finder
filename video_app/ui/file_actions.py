import os
import subprocess
import sys
from pathlib import Path


def open_in_default_player(path: Path) -> str | None:
    """Open the file with the OS-default application. Returns error message or None."""
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return None
    except OSError as e:
        return str(e)


def show_in_explorer(file_path: Path) -> str | None:
    """Open the file manager with this file selected."""
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(file_path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(file_path)])
        else:
            subprocess.Popen(["xdg-open", str(file_path.parent)])
        return None
    except OSError as e:
        return str(e)


def open_folder_in_explorer(folder_path: Path) -> str | None:
    """Open the file manager at this folder."""
    try:
        if sys.platform == "win32":
            os.startfile(str(folder_path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder_path)])
        else:
            subprocess.Popen(["xdg-open", str(folder_path)])
        return None
    except OSError as e:
        return str(e)
