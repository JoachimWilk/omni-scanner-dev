"""Pasek postępu liczony w plikach lub bajtach, z ETA."""
from __future__ import annotations

import sys
import time


def fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_eta(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class Progress:
    def __init__(self, label: str, total: int, unit: str = "files", enabled: bool = True):
        self.label, self.total, self.unit = label, max(total, 0), unit
        self.enabled = enabled and self.total > 0
        self.done = 0
        self._start = time.time()
        self._last = 0.0

    def advance(self, n: int = 1) -> None:
        self.done += n
        if not self.enabled:
            return
        now = time.time()
        if now - self._last < 0.25 and self.done < self.total:
            return
        self._last = now
        self._print(now)

    def _print(self, now: float) -> None:
        frac = min(self.done / self.total, 1.0) if self.total else 1.0
        elapsed = now - self._start
        eta = fmt_eta(elapsed / frac - elapsed) if frac > 0.01 else "--:--"
        if self.unit == "bytes":
            amount = f"{fmt_bytes(self.done)} / {fmt_bytes(self.total)}"
        else:
            amount = f"{self.done}/{self.total}"
        sys.stdout.write(f"\r  {self.label}: {amount} ({frac:4.0%})  ETA {eta}      ")
        sys.stdout.flush()

    def finish(self) -> None:
        if self.enabled:
            self._print(time.time())
            sys.stdout.write("\n")
            sys.stdout.flush()
