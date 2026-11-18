"""Proste struktury danych współdzielone przez wszystkie moduły."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class FileType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    DOC = "doc"
    OTHER = "other"


class Action(str, Enum):
    KEEP = "keep"   # proponowany oryginał
    COPY = "copy"   # kopia do rozważenia (NIGDY nie "rozkaz usunięcia")


@dataclass(frozen=True)
class FileInfo:
    path: str
    size: int
    mtime_ns: int


@dataclass
class Entry:
    file: FileInfo
    action: Action
    hints: List[str] = field(default_factory=list)


@dataclass
class DuplicateGroup:
    digest: str
    size: int
    entries: List[Entry]

    @property
    def wasted(self) -> int:
        """Miejsce do odzyskania po usunięciu wszystkich kopii poza jedną."""
        return self.size * (len(self.entries) - 1)

    @property
    def keeper(self) -> Optional[Entry]:
        for e in self.entries:
            if e.action is Action.KEEP:
                return e
        return None
