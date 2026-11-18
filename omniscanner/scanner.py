"""Szybkie przeglądanie katalogów (os.scandir) z filtrami, wykluczeniami i rejestrem błędów."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, Iterator, List, Optional

from .config import POSIX_EXCLUDED_PATHS, is_posix
from .models import FileInfo

log = logging.getLogger("omniscanner")

# Atrybuty Windows
_REPARSE_POINT = 0x400            # junction / symlink
_CLOUD_FLAGS = 0x1000 | 0x40000 | 0x400000  # OFFLINE | RECALL_ON_OPEN | RECALL_ON_DATA_ACCESS


@dataclass
class ScanStats:
    dirs_scanned: int = 0
    dirs_excluded: int = 0
    files_seen: int = 0
    files_matched: int = 0
    bytes_matched: int = 0
    cloud_skipped: int = 0
    hardlinks_skipped: int = 0
    errors: int = 0
    error_samples: List[str] = field(default_factory=list)

    def record_error(self, path: str, exc: BaseException) -> None:
        self.errors += 1
        if len(self.error_samples) < 5:
            self.error_samples.append(f"{path!r}: {exc}")
        log.warning("%r | %s", path, exc)


def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(path))


def scan(
    root: str,
    extensions: Optional[FrozenSet[str]] = None,
    *,
    min_size: int = 1,
    exclude_names: Iterable[str] = (),
    skip_paths: Iterable[str] = (),
    stats: Optional[ScanStats] = None,
) -> Iterator[FileInfo]:
    """Zwraca pliki spełniające kryteria. Linki symboliczne, junctions oraz pliki
    "tylko w chmurze" (OneDrive) są pomijane, by nie wpaść w pętle ani nie wymusić pobierania."""
    stats = stats if stats is not None else ScanStats()
    exclude = {n.lower() for n in exclude_names}
    skip = {_norm(p) for p in skip_paths}
    posix_excluded = POSIX_EXCLUDED_PATHS if is_posix() else frozenset()

    stack = [root]
    while stack:
        current = stack.pop()
        try:
            it = os.scandir(current)
        except OSError as exc:
            stats.record_error(current, exc)
            continue
        stats.dirs_scanned += 1
        with it:
            while True:
                try:
                    entry = next(it)
                except StopIteration:
                    break
                except OSError as exc:
                    stats.record_error(current, exc)
                    break

                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        st = entry.stat(follow_symlinks=False)
                        attrs = getattr(st, "st_file_attributes", 0)
                        if (
                            entry.name.lower() in exclude
                            or entry.path in posix_excluded
                            or attrs & _REPARSE_POINT
                            or (skip and _norm(entry.path) in skip)
                        ):
                            stats.dirs_excluded += 1
                            continue
                        stack.append(entry.path)
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue

                    stats.files_seen += 1
                    if extensions is not None:
                        if os.path.splitext(entry.name)[1].lower() not in extensions:
                            continue
                    st = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    stats.record_error(entry.path, exc)
                    continue

                if st.st_size < min_size:
                    continue
                if getattr(st, "st_file_attributes", 0) & _CLOUD_FLAGS:
                    stats.cloud_skipped += 1
                    continue

                stats.files_matched += 1
                stats.bytes_matched += st.st_size
                yield FileInfo(entry.path, st.st_size, st.st_mtime_ns)
