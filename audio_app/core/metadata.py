import json
from pathlib import Path

from audio_app.core.ffmpeg import run
from audio_app.models.audio_metadata import AudioMetadata


def probe(path: Path, ffprobe_path: Path) -> AudioMetadata | None:
    cmd = [
        str(ffprobe_path),
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = run(cmd, capture_output=True, timeout=30)
    except Exception:  # noqa: BLE001
        return None
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout or b"{}")
    except json.JSONDecodeError:
        return None

    fmt = data.get("format", {}) or {}
    streams = data.get("streams", []) or []
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if audio_stream is None:
        return None

    try:
        duration = float(fmt.get("duration") or audio_stream.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0

    try:
        bitrate = int(fmt.get("bit_rate") or audio_stream.get("bit_rate") or 0)
    except (TypeError, ValueError):
        bitrate = 0

    return AudioMetadata(
        duration=duration,
        bitrate=bitrate,
        codec=str(audio_stream.get("codec_name") or ""),
    )
