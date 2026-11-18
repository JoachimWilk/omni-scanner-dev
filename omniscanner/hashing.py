"""Hashowanie: próbka (początek/środek/koniec), pełny SHA-256 i trwały cache w SQLite."""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from pathlib import Path
from typing import Callable, Optional

from .models import FileInfo

log = logging.getLogger("omniscanner")

CHUNK_SIZE = 1024 * 1024          # 1 MB – rozsądny rozmiar bufora dla dysków i SSD
SAMPLE_SIZE = 64 * 1024           # 64 KB na każdą z 3 próbek
FULL_ONLY_MAX = 3 * SAMPLE_SIZE   # pliki do tego rozmiaru hashujemy od razu w całości


def full_hash(path: str, on_bytes: Optional[Callable[[int], None]] = None) -> str:
    sha = hashlib.sha256()
    buf = bytearray(CHUNK_SIZE)
    view = memoryview(buf)
    with open(path, "rb", buffering=0) as f:
        while True:
            n = f.readinto(buf)
            if not n:
                break
            sha.update(view[:n])
            if on_bytes:
                on_bytes(n)
    return sha.hexdigest()


def sample_hash(path: str, size: int) -> str:
    """Hash trzech próbek: początek, środek, koniec. Filtr wstępny, NIE dowód identyczności."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        sha.update(f.read(SAMPLE_SIZE))
        f.seek(max(size // 2 - SAMPLE_SIZE // 2, 0))
        sha.update(f.read(SAMPLE_SIZE))
        f.seek(max(size - SAMPLE_SIZE, 0))
        sha.update(f.read(SAMPLE_SIZE))
    return sha.hexdigest()


class HashCache:
    """Cache hashy: klucz = (ścieżka, rodzaj) + ważność = (rozmiar, mtime_ns).
    Powtórny skan nie czyta ponownie niezmienionych plików. path=None => cache wyłączony."""

    def __init__(self, db_path: Optional[Path]):
        self._conn: Optional[sqlite3.Connection] = None
        self._pending = 0
        if db_path is None:
            return
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                "CREATE TABLE IF NOT EXISTS hashes ("
                " path BLOB NOT NULL, kind TEXT NOT NULL, size INTEGER NOT NULL,"
                " mtime_ns INTEGER NOT NULL, digest TEXT NOT NULL,"
                " PRIMARY KEY (path, kind))"
            )
            conn.commit()
            self._conn = conn
        except (sqlite3.Error, OSError) as exc:
            log.warning("Cache hashy wyłączony: %s", exc)

    def get(self, fi: FileInfo, kind: str) -> Optional[str]:
        if self._conn is None:
            return None
        try:
            row = self._conn.execute(
                "SELECT digest FROM hashes WHERE path=? AND kind=? AND size=? AND mtime_ns=?",
                (os.fsencode(fi.path), kind, fi.size, fi.mtime_ns),
            ).fetchone()
        except sqlite3.Error:
            return None
        return row[0] if row else None

    def put(self, fi: FileInfo, kind: str, digest: str) -> None:
        if self._conn is None:
            return
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO hashes VALUES (?,?,?,?,?)",
                (os.fsencode(fi.path), kind, fi.size, fi.mtime_ns, digest),
            )
            self._pending += 1
            if self._pending >= 500:
                self._conn.commit()
                self._pending = 0
        except sqlite3.Error as exc:
            log.warning("Zapis do cache nie powiódł się: %s", exc)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.commit()
                self._conn.close()
            finally:
                self._conn = None

    def __enter__(self) -> "HashCache":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
