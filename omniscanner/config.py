"""Konfiguracja: rozszerzenia, tryby skanowania, wykluczenia."""
from __future__ import annotations

import os
from typing import FrozenSet, Optional

from .models import FileType

PHOTO_EXT = frozenset({
    ".jpg", ".jpeg", ".jfif", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp",
    ".heic", ".heif",
    ".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".rw2", ".raf",
})
DOCS_EXT = frozenset({
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".txt", ".odt", ".rtf",
})
VIDEO_EXT = frozenset({
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".mpeg", ".mpg", ".3gp",
    ".m4v", ".webm", ".mts", ".m2ts", ".vob",
})

MODES = {
    "1": ("Tylko Zdjęcia", PHOTO_EXT),
    "2": ("Multimedia (Zdjęcia + Wideo)", PHOTO_EXT | VIDEO_EXT),
    "3": ("Biuro (Zdjęcia + Dokumenty)", PHOTO_EXT | DOCS_EXT),
    "4": ("Pełny Audyt (Wszystko)", None),
}

# Foldery pomijane domyślnie (porównanie całej nazwy folderu, bez rozróżniania wielkości liter).
SYSTEM_DIR_NAMES = frozenset({
    "windows", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information", "$windows.~bt", "msocache",
    "appdata", ".git", "node_modules", "__pycache__", ".cache",
    ".trash", ".trashes",
})
# Bezwzględne ścieżki pomijane na systemach POSIX.
POSIX_EXCLUDED_PATHS = frozenset({"/proc", "/sys", "/dev", "/run"})

GIANT_THRESHOLD = 100 * 1024 * 1024  # 100 MB – próg filtra "Giganty" w raporcie


def resolve_mode(choice: str) -> Optional[FrozenSet[str]]:
    """Zwraca zestaw rozszerzeń dla trybu (None = wszystko). Rzuca ValueError przy złym wyborze."""
    key = str(choice).strip()
    if key not in MODES:
        raise ValueError(f"Nieznany tryb: {choice!r}. Dozwolone: {', '.join(MODES)}")
    return MODES[key][1]


def mode_label(choice: str) -> str:
    return MODES[str(choice).strip()][0]


def get_file_type(ext: str) -> FileType:
    ext = ext.lower()
    if ext in PHOTO_EXT:
        return FileType.PHOTO
    if ext in VIDEO_EXT:
        return FileType.VIDEO
    if ext in DOCS_EXT:
        return FileType.DOC
    return FileType.OTHER


def parse_size(text: str) -> int:
    """'1' -> 1 B, '10K', '5M', '2G' (potęgi 1024) -> bajty."""
    t = text.strip().upper()
    mult = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}
    if t and t[-1] in mult:
        return int(float(t[:-1]) * mult[t[-1]])
    return int(t)


def is_posix() -> bool:
    return os.name != "nt"
