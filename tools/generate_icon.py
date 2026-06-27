"""Generate resources/icon.ico from the FilmReelLogo QPainter widget.

Run once before building with PyInstaller / Inno Setup:

    python tools/generate_icon.py

Requires PySide6. Saves a multi-resolution ICO to resources/icon.ico.
"""

import io
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication

from video_app.ui.film_reel_logo import FilmReelLogo


def _render_png(size: int) -> bytes:
    widget = FilmReelLogo(size)
    widget.ensurePolished()
    pixmap = widget.grab()
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buf, "PNG")
    buf.close()
    return bytes(buf.data())


def _write_ico(png_map: dict[int, bytes], out_path: Path) -> None:
    """Assemble a PNG-in-ICO container (Vista+ format)."""
    sizes = sorted(png_map)
    count = len(sizes)

    # ICO file header: 6 bytes
    header = struct.pack("<HHH", 0, 1, count)

    # Each directory entry is 16 bytes
    data_offset = 6 + count * 16
    entries = b""
    image_data = b""
    for size in sizes:
        png = png_map[size]
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        entries += struct.pack(
            "<BBBBHHII",
            w, h,
            0,              # palette size (0 = true-colour)
            0,              # reserved
            1,              # colour planes
            32,             # bits per pixel
            len(png),
            data_offset + len(image_data),
        )
        image_data += png

    out_path.write_bytes(header + entries + image_data)


def main() -> None:
    app = QApplication(sys.argv)  # noqa: F841  (needed for QPainter/QPixmap)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    png_map: dict[int, bytes] = {}
    for size in sizes:
        print(f"  rendering {size}x{size}...", end=" ", flush=True)
        png_map[size] = _render_png(size)
        print(f"{len(png_map[size])} bytes")

    out = Path(__file__).resolve().parent.parent / "resources" / "icon.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_ico(png_map, out)
    print(f"\nWritten: {out}  ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
