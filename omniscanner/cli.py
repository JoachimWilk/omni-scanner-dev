"""Interfejs wiersza poleceń: tryb nieinteraktywny (argparse) lub dialog, gdy brakuje argumentów."""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Optional

from . import __version__
from .config import MODES, SYSTEM_DIR_NAMES, mode_label, parse_size, resolve_mode
from .core import run_scan
from .progress import fmt_bytes
from .report import build_data, write_csv, write_html, write_json

SESSION_ID = time.strftime("%Y%m%d_%H%M%S")


def _enable_ansi() -> bool:
    """Włącza kolory ANSI (Windows 10+ przez WinAPI, bez hacka os.system(''))."""
    if os.name != "nt":
        return sys.stdout.isatty()
    try:
        import ctypes
        kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


class Colors:
    def __init__(self, on: bool):
        self.blue, self.green, self.yellow, self.red, self.bold, self.end = (
            ("\033[94m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[0m") if on else ("",) * 6
        )


def normalize_path(raw: str) -> str:
    p = raw.strip().strip('"').strip("'")
    if os.name == "nt" and re.fullmatch(r"[A-Za-z]:", p):
        p += "\\"
    return os.path.abspath(os.path.expanduser(p))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="omniscanner",
        description="Szuka duplikatów plików (bajt w bajt). Skaner nic nie usuwa ani nie modyfikuje.",
    )
    p.add_argument("--mode", choices=sorted(MODES), help="1=Zdjęcia, 2=Multimedia, 3=Biuro, 4=Wszystko")
    p.add_argument("--path", help="Folder lub dysk do przeskanowania")
    p.add_argument("--min-size", default="1", help="Minimalny rozmiar pliku, np. 500K, 5M (domyślnie 1 B)")
    p.add_argument("--exclude", action="append", default=[], metavar="NAZWA",
                   help="Dodatkowa nazwa folderu do pominięcia (można powtarzać)")
    p.add_argument("--include-system", action="store_true",
                   help="Nie pomijaj folderów systemowych (Windows, Program Files, AppData, .git…)")
    p.add_argument("--out", help="Folder na raporty (domyślnie: 'omniscanner_reports' obok skryptu)")
    p.add_argument("--no-cache", action="store_true", help="Wyłącz cache hashy")
    p.add_argument("--csv", action="store_true", help="Zapisz też raport CSV")
    p.add_argument("--version", action="version", version=f"OmniScanner {__version__}")
    return p


def _ask_mode(c: Colors) -> str:
    print(f"{c.yellow}Wybierz zakres skanowania:{c.end}")
    for key, (label, _) in MODES.items():
        print(f"  {c.bold}[{key}]{c.end} {label}")
    while True:
        choice = input(f"\n{c.bold}Wybór (1-4):{c.end} ").strip()
        try:
            resolve_mode(choice)
            return choice
        except ValueError:
            print(f"{c.red}[X] Wpisz cyfrę od 1 do 4.{c.end}")


def _ask_path(c: Colors) -> str:
    while True:
        path = normalize_path(input(f"{c.bold}Podaj ścieżkę (np. D:\\ lub /home/ja/Zdjecia):{c.end} "))
        if os.path.isdir(path):
            return path
        print(f"{c.red}[X] To nie jest istniejący folder.{c.end}")


def _say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def main(argv: Optional[List[str]] = None, base_dir: Optional[Path] = None) -> int:
    args = build_parser().parse_args(argv)
    c = Colors(_enable_ansi())
    interactive = args.mode is None or args.path is None

    print(f"\n{c.blue}{'=' * 60}{c.end}")
    print(f"{c.blue}{c.bold}          OMNI SCANNER v{__version__}{c.end}")
    print(f"{c.blue}{'=' * 60}{c.end}")

    try:
        mode = args.mode or _ask_mode(c)
        root = normalize_path(args.path) if args.path else _ask_path(c)
    except (EOFError, KeyboardInterrupt):
        print("\nPrzerwano.")
        return 130
    if not os.path.isdir(root):
        print(f"{c.red}[X] Błędna ścieżka: {root}{c.end}")
        return 1
    try:
        min_size = parse_size(args.min_size)
    except ValueError:
        print(f"{c.red}[X] Niepoprawny --min-size: {args.min_size!r}{c.end}")
        return 2

    out_dir = Path(args.out) if args.out else (Path(base_dir) if base_dir else Path.cwd()) / "omniscanner_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"error_{SESSION_ID}.log"
    handler = logging.FileHandler(log_path, encoding="utf-8", delay=True)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", "%H:%M:%S"))
    logging.getLogger("omniscanner").addHandler(handler)
    logging.getLogger("omniscanner").setLevel(logging.INFO)

    exclude = set(args.exclude)
    if not args.include_system:
        exclude |= SYSTEM_DIR_NAMES

    start = time.time()
    rc = 0
    try:
        result = run_scan(
            root, resolve_mode(mode),
            min_size=min_size, exclude_names=exclude, skip_paths=[out_dir],
            cache_path=None if args.no_cache else out_dir / "hash_cache.sqlite3",
            progress=sys.stdout.isatty(), say=_say,
        )
    except KeyboardInterrupt:
        print(f"\n{c.yellow}[!] Przerwano. Policzone hashe zostały zapisane w cache, "
              f"kolejne uruchomienie wznowi pracę niemal od razu.{c.end}")
        rc = 130
    else:
        s = result.stats
        if s.errors:
            print(f"{c.yellow}[!] Nie udało się odczytać {s.errors} elementów (np. brak uprawnień). "
                  f"Skan jest niepełny. Szczegóły: {log_path}{c.end}")
        if s.hardlinks_skipped:
            print(f"    Pominięto {s.hardlinks_skipped} twardych linków (to ten sam plik na dysku).")
        if result.groups:
            data = build_data(result, root, mode_label(mode))
            json_path = out_dir / f"wyniki_{SESSION_ID}.json"
            html_path = out_dir / f"raport_{SESSION_ID}.html"
            write_json(json_path, data)            # najpierw dane – raport HTML jest tylko widokiem
            write_html(html_path, data)
            if args.csv:
                write_csv(out_dir / f"wyniki_{SESSION_ID}.csv", data)
            print(f"\n{c.green}{'=' * 60}{c.end}")
            print(f"🏆 {c.bold}GOTOWE!{c.end}  Grup duplikatów: {len(result.groups)}")
            print(f"Raport: {c.yellow}{html_path}{c.end}")
            print(f"Do odzyskania: {c.green}{fmt_bytes(result.wasted)}{c.end} "
                  f"w {time.time() - start:.1f}s")
            print(f"{c.green}{'=' * 60}{c.end}\n")
        else:
            print(f"\n{c.yellow}[!] Brak duplikatów.{c.end}")

    if interactive:
        try:
            input(f"\n{c.bold}Naciśnij Enter, aby zamknąć...{c.end}")
        except (EOFError, KeyboardInterrupt):
            pass
    return rc
