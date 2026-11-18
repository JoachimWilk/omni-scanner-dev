# OmniScanner v1.5 "Safe Edition" 🛡️
### Bezpieczny audyt duplikatów zdjęć, wideo i dokumentów

![license](https://img.shields.io/badge/license-MIT-orange)
![version](https://img.shields.io/badge/version-1.5-green)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![platform](https://img.shields.io/badge/platform-linux%20|%20macos%20|%20windows-lightgrey)

**OmniScanner** znajduje pliki **identyczne co do bajta** (zdjęcia, wideo, dokumenty) i pokazuje je w interaktywnym raporcie HTML.
Skaner **niczego nie usuwa ani nie modyfikuje**. Decyzję podejmujesz Ty.

---

## 🚀 Szybki start

```bash
python omni_scanner.py                      # tryb interaktywny (dialog)
python omni_scanner.py --mode 2 --path D:\  # tryb nieinteraktywny
```

Raport: folder `omniscanner_reports/` obok skryptu (`raport_*.html`, `wyniki_*.json`, opcjonalnie `.csv`).
Wymagany **Python 3.8+**, brak zewnętrznych zależności.

### Tryby skanowania

| Tryb | Zakres |
|---|---|
| **1** | Tylko zdjęcia (w tym HEIC, WEBP, RAW) |
| **2** | Zdjęcia + wideo (najwięcej odzyskanego miejsca) |
| **3** | Zdjęcia + dokumenty (PDF, Office, TXT…) |
| **4** | Pełny audyt: wszystkie pliki (foldery systemowe pomijane, patrz niżej) |

### Opcje CLI

| Opcja | Opis |
|---|---|
| `--mode {1,2,3,4}` / `--path` | Pominięcie dialogu |
| `--min-size 5M` | Ignoruj pliki mniejsze niż 5 MB (`K`, `M`, `G`) |
| `--exclude NAZWA` | Dodatkowy folder do pominięcia (powtarzalne) |
| `--include-system` | Nie pomijaj folderów systemowych |
| `--out FOLDER` | Gdzie zapisać raporty |
| `--csv` | Dodatkowo zapisz CSV |
| `--no-cache` | Wyłącz cache hashy |

---

## 🧠 Jak to działa (uczciwie)

Potok trzyetapowy. Każdy kolejny etap czyta więcej danych, ale dostaje coraz mniej plików:

1. **Rozmiar.** Plik o unikalnym rozmiarze nie może mieć duplikatu i nie jest w ogóle czytany.
2. **Hash próbki** (początek + środek + koniec, po 64 KB). *To tylko filtr wstępny*: szybko odrzuca pliki o tym samym rozmiarze, ale różnej treści.
3. **Pełny SHA-256.** Dopiero on potwierdza duplikat. Raport nigdy nie zawiera dopasowań opartych wyłącznie na próbce.

> ⚠️ **Szybkość:** pliki *unikalne* są odrzucane w ułamku sekundy, ale **prawdziwy duplikat 10 GB musi zostać przeczytany w całości**. Żeby go potwierdzić, nie da się tego uniknąć. Pasek postępu pokazuje bajty i ETA.

**Cache hashy** (SQLite, `hash_cache.sqlite3`) pamięta wyniki dla niezmienionych plików (rozmiar + czas modyfikacji). Powtórny skan, a także wznowienie po `Ctrl+C`, trwa sekundy.

---

## 🛡 Bezpieczeństwo

* **Zero modułu usuwania.** Skaner tylko czyta pliki. Zapisuje wyłącznie własne raporty, log i cache w folderze `omniscanner_reports`.
* **W każdej grupie dokładnie jeden plik jest „proponowanym oryginałem”.** Pozostałe to *„kopie do rozważenia”*. Nie ma sytuacji, w której cała grupa jest oznaczona do skasowania.
* **Jak wybierany jest oryginał?** Preferowane są pliki bez folderów typu `Desktop/Pulpit/Downloads/Temp/Backup/Kopia`, bez „kopii” w nazwie (`kopia_x`, `x - Copy`, `x (1)`), a przy remisie starsze. Porównujemy **całe nazwy folderów**, więc `Templates_wesele` i `Copyright` nie są traktowane jak śmieci. To heurystyka, więc zawsze sprawdź sam.
* **Twarde linki** (ten sam plik pod dwiema ścieżkami) nie są duplikatami. Usunięcie jednego nic nie odzyska. Skaner je pomija.
* **Pomijane domyślnie:** `Windows`, `Program Files`, `ProgramData`, `AppData`, `$Recycle.Bin`, `.git`, `node_modules`, `/proc /sys /dev /run`, własny folder raportów, linki symboliczne i junctions oraz pliki OneDrive „tylko w chmurze” (żeby ich nie pobierać).
* **Raport HTML jest odporny na dziwne nazwy plików** (`"`, `&`, `<`, nie-UTF-8). Dane są osadzone jako JSON i wstawiane przez `textContent`.
* **Błędy nie są ukrywane.** Pliki bez dostępu są zliczane i zapisywane w `error_*.log`. Podsumowanie ostrzega, że skan był niepełny.

---

## ⚠️ Ograniczenia

* Wykrywane są tylko duplikaty **bajt w bajt**. Ten sam film w innym kodeku, zdjęcie po zmianie rozmiaru lub z innym EXIF to dla skanera *różne pliki* (podobieństwo percepcyjne jest w planach).
* Linki symboliczne są pomijane, nie są śledzone.
* Skanowanie jest jednowątkowe (świadomie: na HDD wątki zwykle spowalniają odczyt).

---

## 🧪 Testy i struktura

```bash
python -m unittest discover -s tests -t . -v     # lub: pytest
python setup_test.py                              # demo do ręcznego obejrzenia raportu
```

```
omni_scanner.py          # punkt wejścia (kompatybilny z v1.4)
omniscanner/
  config.py              # rozszerzenia, tryby, wykluczenia
  models.py              # FileInfo, Entry, DuplicateGroup, enumy
  scanner.py             # os.scandir, filtry, rejestr błędów
  hashing.py             # hash próbki, pełny SHA-256, cache SQLite
  grouping.py            # potok rozmiar→próbka→pełny hash, wybór oryginału
  core.py                # run_scan()
  report.py + templates/ # JSON, HTML, CSV
  cli.py, progress.py
tests/                   # 25 testów (regresje po błędach z v1.4)
```

## 📜 Historia zmian

**1.5 "Safe Edition"**: sugestie per grupa (zawsze jeden oryginał), pomijanie hardlinków i folderów systemowych, escapowanie raportu, walidacja trybu, potok z hashem próbki, cache SQLite, postęp w bajtach z ETA, logowanie błędów, `argparse`, JSON/CSV, nowe formaty (HEIC, WEBP, WEBM, MTS…), testy, modularna struktura.
**1.4 "Multimedia Edition"**: wsparcie dla wideo, kolory w raporcie.

**Autor:** JoachimWilk

## 🤖 Vibe Coding
Projekt powstał w koncepcji **Vibe Coding** przy wsparciu narzędzi AI ([Gemini](https://gemini.google.com), [Claude](https://claude.ai)).
