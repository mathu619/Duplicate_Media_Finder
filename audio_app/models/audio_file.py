from dataclasses import dataclass
from pathlib import Path

from audio_app.models.audio_metadata import AudioMetadata


@dataclass
class AudioFile:
    path: Path
    size: int
    mtime: float
    metadata: AudioMetadata | None = None
