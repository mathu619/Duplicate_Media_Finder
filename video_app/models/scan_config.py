from dataclasses import dataclass, field
from enum import Enum


class DetectionTier(Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
    DEEP_FAST = "deep_fast"
    DEEP_SLOW = "deep_slow"

    @property
    def label(self) -> str:
        return {
            DetectionTier.BASIC: "Basic — metadata only (seconds)",
            DetectionTier.ADVANCED: "Advanced — visual fingerprint (minutes)",
            DetectionTier.DEEP_FAST: "Deep (Fast) — audio fingerprint",
            DetectionTier.DEEP_SLOW: "Deep (Slow) — full video match, handles edits",
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
