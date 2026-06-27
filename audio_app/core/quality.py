from audio_app.models.audio_file import AudioFile


def quality_key(f: AudioFile) -> tuple:
    """Higher tuple = better. Used to pick the keeper when flagging duplicates."""
    m = f.metadata
    bitrate = m.bitrate if m else 0
    duration = m.duration if m else 0.0
    return (bitrate, duration, f.size)


def pick_best_index(files: list[AudioFile]) -> int:
    if not files:
        return 0
    best_i = 0
    best_k = quality_key(files[0])
    for i in range(1, len(files)):
        k = quality_key(files[i])
        if k > best_k:
            best_k = k
            best_i = i
    return best_i
