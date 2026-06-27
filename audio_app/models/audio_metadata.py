from dataclasses import dataclass


@dataclass
class AudioMetadata:
    duration: float
    bitrate: int
    codec: str | None
