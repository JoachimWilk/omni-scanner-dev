import os
import hashlib
import csv
import time
from collections import defaultdict

# --- KONFIGURACJA ---
CHUNK_SIZE = 65536 # Optymalne pod HDD (64KB)
LARGE_FILE_THRESHOLD = 1024 * 1024 * 100 # 100MB

# Grupy rozszerzeń dla trybu SMART
PHOTO_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.raw', '.cr2', '.nef', '.arw', '.dng', '.tiff'}
DOCS_EXT = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.txt', '.odt', '.rtf'}

# Generujemy wspólny znacznik czasu dla nazewnictwa plików w tej sesji
SESSION_ID = time.strftime("%Y%m%d_%H%M%S")

def log_error(message):
    """Zapisuje błędy do uinikalnego pliku, zamiast zaśmiecać konsolę."""
    log_file = f"error_{SESSION_ID}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")

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
        log_error(f"Błąd dostępu: {file_path} | {e}")
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
            except OSError as e:
                log_error(f"Nie udało się odczytać rozmiaru: {full_path} | {e}")
                continue
    
    # Faza 2: Hashowanie (Precyzyjne)
    potential = {s: p for s, p in files_by_size.items() if len(p) > 1}
    num_to_hash = sum(len(p) for p in potential.values())

    print(f"[{time.strftime('%H:%M:%S')}] KROK 2: Hashowanie SHA-256 dla {num_to_hash} plików ...")

    duplicates = defaultdict(list)
    processed = 0
    total_wasted_size = 0

    for size, paths in potential.items():
        group_hashes = defaultdict(list)
        for path in paths:
            h = calculate_sha256(path)
            if h:
                group_hashes[h].append(path)
            processed += 1

            if processed % 5 == 0 or processed == num_to_hash:
                print(f" Postęp: {processed}/{num_to_hash} ({(processed/num_to_hash)*100:.1f}%)", end='\r')
        
        # Analiza wyników wewnątrz grupy o tym samym rozmiarze
        for h, duplicated_paths in group_hashes.items():
            if len(duplicated_paths) > 1:
                duplicates[h].extend(duplicated_paths)
                # Rozmiar marnowany = (ilosc kopii - 1) * rozmiar pliku
                total_wasted_size += size * (len(duplicated_paths) - 1)

    return duplicates, total_wasted_size

def save_omni_csv(results, total_wasted):
    output_file = f"raport_omni_{SESSION_ID}.csv"

    try:
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['Hash (Fragment)', 'Nazwa', 'Typ', 'Rozmiar (MB)', 'Katalog'])

            # Sortujemy grupy, zeby najwieksze pliki byly na gorze (opcjonalne)
            for h, paths in results.items():
                for p in paths:
                    ext = os.path.splitext(p)[1].lower()
                    try:
                        size_mb = round(os.path.getsize(p) / (1024*1024), 2)
                    except OSError:
                        size_mb =  0 
                    writer.writerow([h[:10], os.path.basename(p), get_file_type(ext), size_mb, os.path.dirname(p)])
                writer.writerow(['---'] * 5)
        
        wasted_gb = round(total_wasted / (1024**3), 2)
        print(f"\n\n" + "="*50)
        print(f" GOTOWE! Wynik zapisany w: {output_file}")
        print(f" Logi błędów (jeśli wystąpiły): error_{SESSION_ID}.log")
        print(f" Potencjalne miejsce do odzyskania: {wasted_gb} GB")
    except PermissionError:
        print(f"\nBŁĄD: Plik CSV jest otwarty w Excelu. Zamknij go i spróbuj ponownie.")

if __name__ == "__main__":
    print("=== OMNI SCANNER v1.2 ===")
    print("1. Tylko Zdjęcia")
    print("2. Zdjęcia + Dokumenty")
    print("3. Wszystkie pliki (Głęboki skan)")
    choice = input("Wybierz tryb (1/2/3): ").strip()

    path = input("Podaj ścieżkę (np. D:\\ lub /home/user): ").strip().replace('"', '')

    if os.path.exists(path):
        start_time = time.time()
        dups, wasted = run_omni_scanner(path, choice)
        if dups:
            save_omni_csv(dups, wasted)
        else:
            print("\nNie znaleziono żadnych duplikatów.")
        duration = round(time.time() - start_time, 2)
        print(f"Czas pracy: {duration} s.\n")
    else:
        print("Ścieżka nie istnieje!")
