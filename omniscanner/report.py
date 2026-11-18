"""Raporty: JSON (źródło prawdy), HTML (interaktywny, bez wstrzykiwania kodu) i opcjonalnie CSV."""
from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from . import __version__
from .config import GIANT_THRESHOLD, get_file_type
from .core import ScanResult

_TEMPLATE = Path(__file__).with_name("templates") / "report.html"


def build_data(result: ScanResult, root: str, mode: str) -> Dict[str, Any]:
    groups: List[Dict[str, Any]] = []
    for g in result.groups:
        groups.append({
            "digest": g.digest,
            "size": g.size,
            "wasted": g.wasted,
            "entries": [
                {
                    "path": e.file.path,
                    "name": os.path.basename(e.file.path),
                    "type": get_file_type(os.path.splitext(e.file.path)[1]).value,
                    "action": e.action.value,
                    "hints": e.hints,
                    "mtime": int(e.file.mtime_ns // 1_000_000_000),
                }
                for e in g.entries
            ],
        })
    s = result.stats
    return {
        "version": __version__,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "root": root,
        "mode": mode,
        "giant_threshold": GIANT_THRESHOLD,
        "summary": {
            "groups": len(groups),
            "wasted": result.wasted,
            "files_matched": s.files_matched,
            "dirs_scanned": s.dirs_scanned,
            "dirs_excluded": s.dirs_excluded,
            "hardlinks_skipped": s.hardlinks_skipped,
            "cloud_skipped": s.cloud_skipped,
            "errors": s.errors,
        },
        "groups": groups,
    }


def _json_safe(data: Dict[str, Any]) -> str:
    # ensure_ascii=True zamienia też "nie-UTF-8" nazwy plików (surrogates) na bezpieczne \uXXXX.
    return json.dumps(data, ensure_ascii=True)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    Path(path).write_text(_json_safe(data), encoding="ascii")


def write_html(path: Path, data: Dict[str, Any]) -> None:
    payload = _json_safe(data)
    # Dane siedzą w <script type="application/json">; neutralizujemy znaki mogące je zamknąć.
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = _TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", payload)
    Path(path).write_text(html, encoding="utf-8")


def write_csv(path: Path, data: Dict[str, Any]) -> None:
    with open(path, "w", newline="", encoding="utf-8", errors="backslashreplace") as f:
        w = csv.writer(f)
        w.writerow(["group", "digest", "size_bytes", "action", "type", "path", "hints"])
        for i, g in enumerate(data["groups"], 1):
            for e in g["entries"]:
                w.writerow([i, g["digest"], g["size"], e["action"], e["type"], e["path"],
                            "; ".join(e["hints"])])
