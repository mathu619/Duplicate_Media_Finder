from dataclasses import dataclass
from pathlib import Path

from video_app.models.video_metadata import VideoMetadata


@dataclass
class VideoFile:
    path: Path
    size: int
    mtime: float
    metadata: VideoMetadata | None = None
