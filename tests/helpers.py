import os
import tempfile
import unittest
from pathlib import Path


class TmpCase(unittest.TestCase):
    """Baza testów: każdy test dostaje świeży folder tymczasowy w self.root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def make(self, rel: str, data: bytes, mtime: float = None) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        if mtime is not None:
            os.utime(p, (mtime, mtime))
        return p

    @staticmethod
    def names(groups):
        return sorted(sorted(os.path.basename(e.file.path) for e in g.entries) for g in groups)
