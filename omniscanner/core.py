"""Wysokopoziomowe API: run_scan() – skan + wykrywanie duplikatów."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, FrozenSet, Iterable, List, Optional

from .grouping import find_duplicates
from .hashing import HashCache
from .models import DuplicateGroup
from .scanner import ScanStats, scan


@dataclass
class ScanResult:
    groups: List[DuplicateGroup]
    stats: ScanStats

    @property
    def wasted(self) -> int:
        return sum(g.wasted for g in self.groups)


def run_scan(
    root: str,
    extensions: Optional[FrozenSet[str]] = None,
    *,
    min_size: int = 1,
    exclude_names: Iterable[str] = (),
    skip_paths: Iterable[str] = (),
    cache_path: Optional[Path] = None,
    progress: bool = False,
    say: Optional[Callable[[str], None]] = None,
) -> ScanResult:
    say = say or (lambda _m: None)
    stats = ScanStats()
    say("KROK 1/3: Skanowanie struktury katalogów...")
    files = list(scan(root, extensions, min_size=min_size, exclude_names=exclude_names,
                      skip_paths=skip_paths, stats=stats))
    say(f"  dopasowano {stats.files_matched} plików w {stats.dirs_scanned} folderach "
        f"(pominięto folderów: {stats.dirs_excluded}).")
    # `with` gwarantuje zapis cache także po Ctrl+C – kolejny skan wznowi pracę niemal od razu.
    with HashCache(cache_path) as cache:
        groups = find_duplicates(files, cache, stats, progress=progress, say=say)
    return ScanResult(groups, stats)
