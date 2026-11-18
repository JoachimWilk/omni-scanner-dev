"""Generator środowiska testowego: python setup_test.py [folder]  (domyślnie ./test_lab)

To NIE są testy automatyczne (te są w katalogu tests/) – to demo do ręcznego obejrzenia raportu.
Po wygenerowaniu uruchom:  python omni_scanner.py --mode 2 --path test_lab
Oczekiwane grupy duplikatów: foto1 (3 pliki), wideo1 (2 pliki), dokument (2 pliki).
"""
import os
import sys


def write(base, rel, data):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path


def create_test_env(base="test_lab"):
    foto = b"to_jest_identyczna_zawartosc_123"
    wideo = b"to_jest_zawartosc_wideo_123"

    # 1. Oryginał + dokładne kopie (inna nazwa, inny folder)
    write(base, "foto1.jpg", foto)
    write(base, "backup/stare/kopia_foto1.jpg", foto)
    write(base, "Desktop/foto1 (1).jpg", foto)              # trzecia kopia -> grupa 3-plikowa
    write(base, "wideo1.mov", wideo)
    write(base, "backup/stare/kopia_wideo1.mov", wideo)

    # 2. Ten sam ROZMIAR, inna treść – prawdziwy test czujności hasha (długości są równe)
    pomylka_foto = foto[::-1]
    pomylka_wideo = wideo[::-1]
    assert len(pomylka_foto) == len(foto) and pomylka_foto != foto
    assert len(pomylka_wideo) == len(wideo) and pomylka_wideo != wideo
    write(base, "foto_pomyłka.jpg", pomylka_foto)
    write(base, "wideo_pomyłka.mov", pomylka_wideo)

    # 3. Unikalne pliki
    write(base, "wakacje/unikalne.jpg", b"unikalna_tresc_456789")
    write(base, "wakacje/unikalny.mov", b"unikalna_111111_tresc_")

    # 4. Duży plik (>192 KB) różniący się tylko w środku – sprawdza pełny hash po filtrze próbek
    duzy = bytearray(os.urandom(400_000))
    write(base, "wakacje/duze1.mov", bytes(duzy))
    write(base, "backup/duze1_kopia.mov", bytes(duzy))
    duzy[100_000] ^= 0xFF
    write(base, "wakacje/duze2_prawie_to_samo.mov", bytes(duzy))

    # 5. Dokument + pułapki nazw (nie mogą być traktowane jak "śmieci")
    write(base, "Templates_wesele/umowa.pdf", b"%PDF-1.4 umowa")
    write(base, "Copyright/umowa.pdf", b"%PDF-1.4 umowa")

    # 6. Twardy link – NIE jest duplikatem (nic nie odzyskasz)
    if hasattr(os, "link"):
        try:
            os.link(os.path.join(base, "wakacje/unikalne.jpg"), os.path.join(base, "wakacje/hardlink.jpg"))
        except OSError:
            pass

    print(f"Struktura testowa stworzona w folderze: {os.path.abspath(base)}")


if __name__ == "__main__":
    create_test_env(sys.argv[1] if len(sys.argv) > 1 else "test_lab")
