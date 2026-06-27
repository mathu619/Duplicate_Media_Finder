from pathlib import Path

from send2trash import send2trash


def send_to_recycle_bin(paths: list[Path]) -> tuple[list[Path], list[tuple[Path, str]]]:
    succeeded: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for p in paths:
        try:
            send2trash(str(p))
            succeeded.append(p)
        except Exception as e:  # noqa: BLE001
            failed.append((p, str(e)))
    return succeeded, failed
