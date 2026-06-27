import os
import sqlite3
from pathlib import Path

from video_app.models.video_metadata import VideoMetadata


def _default_cache_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    directory = Path(base) / "DuplicateVideoFinder"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "cache.sqlite"


def cache_stats(db_path: Path | None = None) -> dict:
    """Read-only snapshot of cache disk usage and row counts. Safe to call any time."""
    db = db_path or _default_cache_path()
    bytes_total = 0
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db) + suffix)
        if p.exists():
            bytes_total += p.stat().st_size
    videos = 0
    if db.exists():
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'"
                ).fetchone()
                if row:
                    videos = conn.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
            finally:
                conn.close()
        except sqlite3.Error:
            pass
    return {"size_bytes": bytes_total, "videos": videos}


class FingerprintCache:
    _COMMIT_EVERY = 200

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _default_cache_path()
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS file_hash (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                quick_hash TEXT,
                full_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS metadata (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                duration REAL NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                bitrate INTEGER NOT NULL,
                video_codec TEXT NOT NULL,
                audio_codec TEXT
            );
            CREATE TABLE IF NOT EXISTS frame_fingerprint (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                hashes BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audio_fingerprint (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                duration REAL NOT NULL,
                fingerprint BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS uniform_frame_fingerprint (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                hashes BLOB NOT NULL
            );
            """
        )
        self._conn.commit()
        self._pending = 0
        self._hits = 0
        self._computes = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def computes(self) -> int:
        return self._computes

    # ---------- byte hash ----------

    def get_hashes(self, path: str, size: int, mtime: float) -> tuple[str | None, str | None] | None:
        row = self._conn.execute(
            "SELECT size, mtime, quick_hash, full_hash FROM file_hash WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None or row[0] != size or abs(row[1] - mtime) > 1e-3:
            return None
        self._hits += 1
        return (row[2], row[3])

    def put_hashes(
        self,
        path: str,
        size: int,
        mtime: float,
        quick_hash: str | None,
        full_hash: str | None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO file_hash (path, size, mtime, quick_hash, full_hash)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size, mtime=excluded.mtime,
                quick_hash=excluded.quick_hash, full_hash=excluded.full_hash
            """,
            (path, size, mtime, quick_hash, full_hash),
        )
        self._tick()

    # ---------- metadata ----------

    def get_metadata(self, path: str, size: int, mtime: float) -> VideoMetadata | None:
        row = self._conn.execute(
            """
            SELECT size, mtime, duration, width, height, bitrate, video_codec, audio_codec
            FROM metadata WHERE path = ?
            """,
            (path,),
        ).fetchone()
        if row is None or row[0] != size or abs(row[1] - mtime) > 1e-3:
            return None
        self._hits += 1
        return VideoMetadata(
            duration=row[2],
            width=row[3],
            height=row[4],
            bitrate=row[5],
            video_codec=row[6],
            audio_codec=row[7],
        )

    def put_metadata(self, path: str, size: int, mtime: float, meta: VideoMetadata) -> None:
        self._conn.execute(
            """
            INSERT INTO metadata (path, size, mtime, duration, width, height, bitrate, video_codec, audio_codec)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size, mtime=excluded.mtime,
                duration=excluded.duration, width=excluded.width, height=excluded.height,
                bitrate=excluded.bitrate, video_codec=excluded.video_codec, audio_codec=excluded.audio_codec
            """,
            (
                path, size, mtime,
                meta.duration, meta.width, meta.height, meta.bitrate,
                meta.video_codec, meta.audio_codec,
            ),
        )
        self._tick()

    # ---------- frame fingerprint ----------

    def get_frame_fingerprint(self, path: str, size: int, mtime: float) -> bytes | None:
        row = self._conn.execute(
            "SELECT size, mtime, hashes FROM frame_fingerprint WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None or row[0] != size or abs(row[1] - mtime) > 1e-3:
            return None
        self._hits += 1
        return row[2]

    def put_frame_fingerprint(self, path: str, size: int, mtime: float, blob: bytes) -> None:
        self._conn.execute(
            """
            INSERT INTO frame_fingerprint (path, size, mtime, hashes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size, mtime=excluded.mtime, hashes=excluded.hashes
            """,
            (path, size, mtime, blob),
        )
        self._tick()

    # ---------- audio fingerprint ----------

    def get_audio_fingerprint(
        self, path: str, size: int, mtime: float
    ) -> tuple[float, bytes] | None:
        row = self._conn.execute(
            "SELECT size, mtime, duration, fingerprint FROM audio_fingerprint WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None or row[0] != size or abs(row[1] - mtime) > 1e-3:
            return None
        self._hits += 1
        return (row[2], row[3])

    def put_audio_fingerprint(
        self,
        path: str,
        size: int,
        mtime: float,
        duration: float,
        blob: bytes,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO audio_fingerprint (path, size, mtime, duration, fingerprint)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size, mtime=excluded.mtime,
                duration=excluded.duration, fingerprint=excluded.fingerprint
            """,
            (path, size, mtime, duration, blob),
        )
        self._tick()

    # ---------- uniform frame fingerprint (Tier 3 Slow) ----------

    def get_uniform_frame_fingerprint(self, path: str, size: int, mtime: float) -> bytes | None:
        row = self._conn.execute(
            "SELECT size, mtime, hashes FROM uniform_frame_fingerprint WHERE path = ?",
            (path,),
        ).fetchone()
        if row is None or row[0] != size or abs(row[1] - mtime) > 1e-3:
            return None
        self._hits += 1
        return row[2]

    def put_uniform_frame_fingerprint(
        self, path: str, size: int, mtime: float, blob: bytes
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO uniform_frame_fingerprint (path, size, mtime, hashes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size, mtime=excluded.mtime, hashes=excluded.hashes
            """,
            (path, size, mtime, blob),
        )
        self._tick()

    # ---------- lifecycle ----------

    def _tick(self) -> None:
        self._pending += 1
        self._computes += 1
        if self._pending >= self._COMMIT_EVERY:
            self._conn.commit()
            self._pending = 0

    def close(self) -> None:
        try:
            self._conn.commit()
        finally:
            self._conn.close()
