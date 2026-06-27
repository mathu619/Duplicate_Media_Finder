from dataclasses import dataclass
from enum import Enum

from audio_app.core.quality import pick_best_index
from audio_app.models.audio_file import AudioFile


class DuplicateKind(Enum):
    SAME_CONTENT = "same_content"
    CONTAINED_CLIP = "contained_clip"


@dataclass
class DuplicateGroup:
    files: list[AudioFile]
    reason: str
    kind: DuplicateKind = DuplicateKind.SAME_CONTENT

    @property
    def wasted_space(self) -> int:
        if len(self.files) <= 1:
            return 0
        if self.kind is DuplicateKind.CONTAINED_CLIP:
            # For contained clips the "winner" is ambiguous by size; savings
            # are approximated as the shortest file in the group.
            return min(f.size for f in self.files)
        keeper = pick_best_index(self.files)
        return sum(f.size for i, f in enumerate(self.files) if i != keeper)
