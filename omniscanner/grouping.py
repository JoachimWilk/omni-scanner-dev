"""Potok wykrywania duplikatów (rozmiar -> próbka -> pełny hash) i wybór proponowanego oryginału."""
from __future__ import annotations

import os
import re
from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from . import hashing
from .hashing import HashCache
from .models import Action, DuplicateGroup, Entry, FileInfo
from .progress import Progress
from .scanner import ScanStats

# --- Heurystyka "który plik jest oryginałem" ---------------------------------------------------
# Porównujemy CAŁE nazwy folderów (nie podciągi): "Templates_wesele" ani "Copyright" nie wpadają.
JUNK_FOLDERS = frozenset({
    "temp", "tmp", "downloads", "pobrane", "desktop", "pulpit",
    "copy", "kopia", "kopie", "copies", "cache", "trash", "kosz",
    "backup", "backups",
})
_SPLIT = re.compile(r"[\\/]+")
# "kopia_foto", "foto - Copy", "foto (1)" – ale nie "Copyright" ani "Contemporary"
_COPY_NAME = re.compile(r"(?i)(^|[^a-z0-9])(copy|kopia|kopie)([^a-z0-9]|$)|\(\d+\)\s*$")


def analyze_path(path: str) -> Tuple[List[str], bool]:
    *folders, name = _SPLIT.split(path)       # niezależnie od systemu: obsługuje / i \
    stem = os.path.splitext(name)[0]
    junk = [seg for seg in folders if seg.lower() in JUNK_FOLDERS]
    return junk, bool(_COPY_NAME.search(stem))


def build_group(digest: str, size: int, files: List[FileInfo]) -> DuplicateGroup:
    """Zawsze dokładnie JEDEN plik dostaje KEEP – to gwarantuje, że żadna grupa nie zostanie
    w całości oznaczona jako kopie."""
    scored = []
    for fi in files:
        junk, copy_name = analyze_path(fi.path)
        score = (len(junk), int(copy_name), fi.mtime_ns, len(fi.path), fi.path)
        scored.append((score, fi, junk, copy_name))
    scored.sort(key=lambda t: t[0])

    entries: List[Entry] = []
    for i, (_, fi, junk, copy_name) in enumerate(scored):
        hints = [f"folder „{j}”" for j in junk]
        if copy_name:
            hints.append("nazwa wygląda jak kopia")
        if i == 0:
            entries.append(Entry(fi, Action.KEEP, ["proponowany oryginał"] + hints))
        else:
            entries.append(Entry(fi, Action.COPY, hints))
    # kopie po keeperze, posortowane ścieżką – raport jest deterministyczny
    entries[1:] = sorted(entries[1:], key=lambda e: e.file.path)
    return DuplicateGroup(digest, size, entries)


# --- Potok --------------------------------------------------------------------------------------
def _drop_hardlinks(files: List[FileInfo]) -> Tuple[List[FileInfo], int]:
    """Twarde linki to ten sam plik na dysku – usunięcie "kopii" nic nie odzyska."""
    seen = set()
    unique: List[FileInfo] = []
    for fi in files:
        try:
            st = os.stat(fi.path)
        except OSError:
            unique.append(fi)  # błąd odczytu zostanie zgłoszony w etapie hashowania
            continue
        if st.st_ino:
            key = (st.st_dev, st.st_ino)
            if key in seen:
                continue
            seen.add(key)
        unique.append(fi)
    return unique, len(files) - len(unique)


def _digest(
    fi: FileInfo, kind: str, cache: HashCache, stats: ScanStats,
    on_bytes: Optional[Callable[[int], None]] = None,
) -> Optional[str]:
    cached = cache.get(fi, kind)
    if cached:
        if on_bytes and kind == "full":
            on_bytes(fi.size)
        return cached
    try:
        if kind == "full":
            digest = hashing.full_hash(fi.path, on_bytes)
        else:
            digest = hashing.sample_hash(fi.path, fi.size)
    except OSError as exc:
        stats.record_error(fi.path, exc)
        return None
    cache.put(fi, kind, digest)
    return digest


def find_duplicates(
    files: Iterable[FileInfo],
    cache: HashCache,
    stats: ScanStats,
    *,
    progress: bool = False,
    say: Callable[[str], None] = lambda _m: None,
) -> List[DuplicateGroup]:
    by_size: Dict[int, List[FileInfo]] = defaultdict(list)
    for fi in files:
        by_size[fi.size].append(fi)

    candidates: Dict[int, List[FileInfo]] = {}
    for size, group in by_size.items():
        if len(group) < 2:
            continue
        unique, skipped = _drop_hardlinks(group)
        stats.hardlinks_skipped += skipped
        if len(unique) > 1:
            candidates[size] = unique

    todo = [fi for g in candidates.values() for fi in g]
    say(f"KROK 2/3: Hash wstępny ({len(todo)} plików o powtarzającym się rozmiarze)...")
    prog = Progress("Hash wstępny", len(todo), "files", enabled=progress)
    stage2: Dict[Tuple[int, str, str], List[FileInfo]] = defaultdict(list)
    for fi in todo:
        kind = "full" if fi.size <= hashing.FULL_ONLY_MAX else "sample"
        d = _digest(fi, kind, cache, stats)
        if d:
            stage2[(fi.size, kind, d)].append(fi)
        prog.advance()
    prog.finish()

    confirmed: List[Tuple[str, int, List[FileInfo]]] = []
    need_full: List[Tuple[int, List[FileInfo]]] = []
    for (size, kind, digest), group in stage2.items():
        if len(group) < 2:
            continue
        if kind == "full":
            confirmed.append((digest, size, group))
        else:
            need_full.append((size, group))

    total_bytes = sum(size * len(g) for size, g in need_full)
    say(f"KROK 3/3: Pełna weryfikacja SHA-256 ({len(need_full)} grup, "
        f"{total_bytes / 1024**3:.2f} GB do odczytania)...")
    prog = Progress("Weryfikacja", total_bytes, "bytes", enabled=progress)
    for size, group in need_full:
        by_digest: Dict[str, List[FileInfo]] = defaultdict(list)
        for fi in group:
            d = _digest(fi, "full", cache, stats, on_bytes=prog.advance)
            if d:
                by_digest[d].append(fi)
        for digest, same in by_digest.items():
            if len(same) > 1:
                confirmed.append((digest, size, same))
    prog.finish()

    groups = [build_group(d, s, f) for d, s, f in confirmed]
    groups.sort(key=lambda g: (-g.wasted, g.digest))
    return groups
