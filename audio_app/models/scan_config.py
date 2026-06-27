from dataclasses import dataclass, field
from enum import Enum


class DetectionTier(Enum):
    BASIC = "basic"
    DEEP_FAST = "deep_fast"
    CONTAINED_CLIPS = "contained_clips"

    @property
    def label(self) -> str:
        return {
            DetectionTier.BASIC: "Basic - exact audio file match",
            DetectionTier.DEEP_FAST: "Deep (Fast) - audio fingerprint",
            DetectionTier.CONTAINED_CLIPS: "Contained Clips - find excerpts inside longer files",
        }[self]


@dataclass
class ScanRoot:
    path: str
    recursive: bool = True


@dataclass
class ScanConfig:
    roots: list[ScanRoot]
    tier: DetectionTier
    extra_files: list[str] = field(default_factory=list)
