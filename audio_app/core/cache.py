import os
import sqlite3
from pathlib import Path

from audio_app.models.audio_metadata import AudioMetadata


def _default_cache_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    directory = Path(base) / "DuplicateAudioFinder"
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
    audio_files = 0
    if db.exists():
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'"
                ).fetchone()
                if row:
                    audio_files = conn.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
            finally:
                conn.close()
        except sqlite3.Error:
            pass
    return {"size_bytes": bytes_total, "audio_files": audio_files}


class FingerprintCache:
    _COMMIT_EVERY = 200
    _METADATA_SCHEMA = """
            CREATE TABLE IF NOT EXISTS metadata (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                duration REAL NOT NULL,
                bitrate INTEGER NOT NULL,
                codec TEXT
            );
            """

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
        self._conn.executescript(self._METADATA_SCHEMA)
        self._reset_legacy_metadata_table()
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

    def _reset_legacy_metadata_table(self) -> None:
        columns = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(metadata)").fetchall()
        }
        if "codec" in columns:
            return
        self._conn.execute("DROP TABLE IF EXISTS metadata")
        self._conn.executescript(self._METADATA_SCHEMA)

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

    def get_metadata(self, path: str, size: int, mtime: float) -> AudioMetadata | None:
        row = self._conn.execute(
            """
            SELECT size, mtime, duration, bitrate, codec
            FROM metadata WHERE path = ?
            """,
            (path,),
        ).fetchone()
        if row is None or row[0] != size or abs(row[1] - mtime) > 1e-3:
            return None
        self._hits += 1
        return AudioMetadata(
            duration=row[2],
            bitrate=row[3],
            codec=row[4],
        )

    def put_metadata(self, path: str, size: int, mtime: float, meta: AudioMetadata) -> None:
        self._conn.execute(
            """
            INSERT INTO metadata (path, size, mtime, duration, bitrate, codec)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size, mtime=excluded.mtime,
                duration=excluded.duration, bitrate=excluded.bitrate, codec=excluded.codec
            """,
            (
                path, size, mtime,
                meta.duration, meta.bitrate, meta.codec,
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
