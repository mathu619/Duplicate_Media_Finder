from dataclasses import dataclass


@dataclass
class VideoMetadata:
    duration: float
    width: int
    height: int
    bitrate: int
    video_codec: str
    audio_codec: str | None

    @property
    def resolution(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "unknown"

    @property
    def pixels(self) -> int:
        return self.width * self.height
