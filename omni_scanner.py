import os
import hashlib
import csv
import time
from collections import defaultdict

# --- KONFIGURACJA ---
CHUNK_SIZE = 65536 # Optymalne pod HDD (64KB)

# Grupy rozszerzeń dla trybu SMART
PHOTO_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.raw', '.cr2', '.nef', '.arw', '.dng', '.tiff'}
DOCS_EXT = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.txt', '.odt', '.rtf'}

def get_file_type(ext):
    if ext in PHOTO_EXT: return "ZDJĘCIE"
    if ext in DOCS_EXT: return "DOKUMENT"
    return "INNY"

def calculate_sha256(file_path):
    """Pancerny odczyt pliku bajt po bajcie."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                sha256.update(chunk)
            return sha256.hexdigest()
    except (OSError, PermissionError) as e:
        print(f"\n[!] Błąd dostępu do: {os.path.basename(file_path)} ({e})")
        return None

def run_omni_scanner(root_path, mode='1'):
    # Faza 1: Skanowanie rozmiarów (Szybkie)
    files_by_size = defaultdict(list)
    total_scanned = 0

    print(f"\n[{time.strftime('%H:%M:%S')}] KROK 1: Analiza struktury plików ...")

    for dirpath, _, filenames in os.walk(root_path):
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()

            # Filtrowanie trybów
            if mode == '1' and ext not in PHOTO_EXT: continue
            if mode == '2' and ext not in PHOTO_EXT and ext not in DOCS_EXT: continue
            # Tryb 3 (Wszystko) przechodzi bez filtrów

            full_path = os.path.join(dirpath, f)
            try:
                size = os.path.getsize(full_path)
                if size > 0:
                    files_by_size[size].append(full_path)
                    total_scanned += 1
            except OSError:
                continue
    
    # Faza 2: Hashowanie (Precyzyjne)
    potential = {s: p for s, p in files_by_size.items() if len(p) > 1}
    num_to_hash = sum(len(p) for p in potential.values())

    print(f"[{time.strftime('%H:%M:%S')}] KROK 2: Hashowanie SHA-256 dla {num_to_hash} plików ...")

    duplicates = defaultdict(list)
    processed = 0

    for size, paths in potential.items():
        for path in paths:
            h = calculate_sha256(path)
            if h:
                duplicates[h].append(path)
                processed += 1
            if processed % 10 == 0 or processed == num_to_hash:
                print(f" Postęp: {processed}/{num_to_hash} ({(processed/num_to_hash)*100:.1f}%)", end='\r')
    return {h: p for h, p in duplicates.items() if len(p) > 1}

def save_omni_csv(results, output_file="raport_omni.csv"):
    try:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['Hash (Fragment)', 'Nazwa', 'Typ', 'Rozmiar (MB)', 'Katalog'])

            for h, paths in results.items():
                for p in paths:
                    ext = os.path.splitext(p)[1].lower()
                    size_mb = round(os.path.getsize(p) / (1024*1024), 2)
                    writer.writerow([h[:10], os.path.basename(p), get_file_type(ext), size_mb, os.path.dirname(p)])
                writer.writerow(['---'] * 5)
        print(f"\n\nGOTOWE! Wynik w pliku: {output_file}")
    except PermissionError:
        print(f"\nBŁĄD: Plik CSV jest otwarty w Excelu. Zamknij go i spróbuj ponownie.")

if __name__ == "__main__":
    print("=== OMNI SCANNER v1.0 ===")
    print("1. Tylko Zdjęcia")
    print("2. Zdjęcia + Dokumenty")
    print("3. Wszystkie pliki (Głęboki skan)")
    choice = input("Wybierz tryb (1/2/3): ").strip()

    path = input("Podaj ścieżkę (np. D:\\ lub /home/user): ").strip().replace('"', '')

    if os.path.exists(path):
        start = time.time()
        dups = run_omni_scanner(path, choice)
        if dups:
            save_omni_csv(dups)
        else:
            print("\nNie znaleziono żadnych duplikatów.")
        print(f"Czas pracy: {round(time.time() - start, 2)} s.")
    else:
        print("Ścieżka nie istnieje!")
