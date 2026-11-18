"""Punkt wejścia kompatybilny z poprzednimi wersjami: `python omni_scanner.py`."""
import sys
from pathlib import Path

from omniscanner.cli import main

if __name__ == "__main__":
    # Raporty trafiają obok skryptu, a nie do bieżącego katalogu roboczego.
    sys.exit(main(base_dir=Path(__file__).resolve().parent))
