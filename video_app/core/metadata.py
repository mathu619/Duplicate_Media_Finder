import json
from pathlib import Path

from video_app.core.ffmpeg import run
from video_app.models.video_metadata import VideoMetadata


def probe(path: Path, ffprobe_path: Path) -> VideoMetadata | None:
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
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video_stream is None:
        return None

    try:
        duration = float(fmt.get("duration") or video_stream.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0

    try:
        bitrate = int(fmt.get("bit_rate") or video_stream.get("bit_rate") or 0)
    except (TypeError, ValueError):
        bitrate = 0

    return VideoMetadata(
        duration=duration,
        width=int(video_stream.get("width") or 0),
        height=int(video_stream.get("height") or 0),
        bitrate=bitrate,
        video_codec=str(video_stream.get("codec_name") or ""),
        audio_codec=str(audio_stream.get("codec_name")) if audio_stream else None,
    )
