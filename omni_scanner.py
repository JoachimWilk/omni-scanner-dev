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

def get_action_suggestion(path):
    path_lower = path.lower()
    trash_triggers = ['temp', 'tmp','downloads', 'pobrane', 'desktop', 'pulpit', 'copy', 'kopia']
    if any(trigger in path_lower for trigger in trash_triggers):
        return "DO USUNIĘCIA"
    return "ZACHOWAJ (ORYGINAŁ?)"

def calculate_fast_hash(file_path):
    """Sprawdza tylko początek i koniec dużych plików, aby zaoszczędzić czas HDD."""
    try:
        size = os.path.getsize(file_path)
        if size < LARGE_FILE_THRESHOLD:
            return calculate_sha256(file_path)
    
    # Dla gigantów: czytaj 64KB z początku i 64KB z końca
        with open(file_path, 'rb') as f:
            start_chunk = f.read(CHUNK_SIZE)
            f.seek(-CHUNK_SIZE, os.SEEK_END)
            end_chunk = f.read(CHUNK_SIZE)
            return hashlib.sha256(start_chunk + end_chunk).hexdigest() + "_fast"
    except Exception as e:
        log_error(f"Błąd Fast-Hash: {file_path} | {e}")
        return None

def calculate_sha256(file_path):
    """Pancerny odczyt pliku bajt po bajcie."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                sha256.update(chunk)
            return sha256.hexdigest()
    except Exception as e:
        log_error(f"Błąd SHA256: {file_path} | {e}")
        return None

def run_omni_scanner(root_path, mode='1'):
    files_by_size = defaultdict(list)
    print(f"\n[{time.strftime('%H:%M:%S')}] KROK 1: Skanowanie rozmiarów...")
    for dirpath, _, filenames in os.walk(root_path):
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if mode == '1' and ext not in PHOTO_EXT: continue
            if mode == '2' and ext not in (PHOTO_EXT | DOCS_EXT): continue
            full_path = os.path.join(dirpath, f)
            try:
                size = os.path.getsize(full_path)
                if size > 0: files_by_size[size].append(full_path)
            except OSError: continue

    potential = {s: p for s, p in files_by_size.items() if len(p) > 1}
    num_to_hash = sum(len(p) for p in potential.values())
    print(f"[{time.strftime('%H:%M:%S')}] KROK 2: Hashowanie ({num_to_hash} plików)...")

    duplicates = defaultdict(list)
    processed = 0
    total_wasted_size = 0

    for size, paths in potential.items():
        temp_hashes = defaultdict(list)
        for path in paths:
            # Używamy FAST-HASH dla prędkości
            h = calculate_fast_hash(path)
            if h: temp_hashes[h].append(path)
            processed += 1
            if processed % 10 == 0: print(f" Postęp: {processed}/{num_to_hash}", end='\r')
        
        for h, dup_paths in temp_hashes.items():
            if len(dup_paths) > 1:
                # Jeśli Fast-Hash wykrył duplikaty dużych plików, weryfikujemy je pełnym SHA256
                if h.endswith("_fast"):
                    verified = defaultdict(list)
                    for dp in dup_paths:
                        vh = calculate_sha256(dp)
                        if vh: verified[vh].append(dp)
                    for vh, v_paths in verified.items():
                        if len(v_paths) > 1:
                            duplicates[vh].extend(v_paths)
                            total_wasted_size += size * (len(v_paths) - 1)
                else:
                    duplicates[h].extend(dup_paths)
                    total_wasted_size += size * (len(dup_paths) - 1)

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

def save_html_report(results, total_wasted, filename):
    wasted_gb = round(total_wasted / (1024**3), 2)
    html_content = f"""
    <html><head><title>OmniScanner Report</title>
    <style>
        body {{ font-family: sans-serif; background: #f4f4f9; padding: 20px; }}
        table {{ border-collapse: collapse; width: 100%; background: white; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #007bff; color: white; }}
        tr:hover {{ background-color: #f1f1f1; }}
        .delete {{ color: red; font-weight: bold; }}
        .keep {{ color: green; font-weight: bold; }}
        .summary {{ background: #333; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
    </style></head><body>
    <div class="summary">
        <h2>Raport OmniScanner</h2>
        <p>Data: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Marnowane miejsce: <b>{wasted_gb} GB</b></p>
    </div>
    <table><tr><th>Typ</th><th>Nazwa</th><th>Rozmiar (MB)</th><th>Sugestia</th><th>Katalog</th></tr>
    """
    for h, paths in results.items():
        for p in paths:
            ext = os.path.splitext(p)[1].lower()
            size_mb = round(os.path.getsize(p) / (1024*1024), 2)
            sug = get_action_suggestion(p)
            sug_class = "delete" if sug == "DO USUNIĘCIA" else "keep"
            html_content += f"<tr><td>{get_file_type(ext)}</td><td>{os.path.basename(p)}</td><td>{size_mb}</td><td class='{sug_class}'>{sug}</td><td>{p}</td></tr>"
    html_content += "</table></body></html>"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    print("=== OMNI SCANNER v1.3 ===")
    print("1. Tylko Zdjęcia")
    print("2. Zdjęcia + Dokumenty")
    print("3. Wszystkie pliki (Głęboki skan)")
    choice = input("Wybierz tryb (1/2/3): ").strip()

    path = input("Podaj ścieżkę (np. D:\\ lub /home/user): ").strip().replace('"', '')

    if os.path.exists(path):
        start = time.time()
        dups, wasted = run_omni_scanner(path, choice)
        if dups:
            timestamp = SESSION_ID
            # Zapisz CSV
            csv_name = f"raport_{timestamp}.csv"
            with open(csv_name, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f, delimiter=';')
                w.writerow(['Hash', 'Nazwa', 'Typ', 'Rozmiar (MB)', 'Sugestia', 'Katalog'])
                for h, paths in dups.items():
                    for p in paths:
                        size_mb = round(os.path.getsize(p) / (1024*1024), 2)
                        w.writerow([h[:10], os.path.basename(p), get_file_type(os.path.splitext(p)[1].lower()), size_mb, get_action_suggestion(p), p])
            
            # Zapisz HTML
            html_name = f"raport_{timestamp}.html"
            save_html_report(dups, wasted, html_name)
            
            print(f"\n\nGOTOWE! Raporty:")
            print(f"- csv:  {csv_name}")
            print(f"- html: {html_name}\n")
            print(f"Odzyskasz: {round(wasted / (1024**3), 2)} GB | Czas: {round(time.time()-start, 2)}s")
        else:
            print("\nBrak duplikatów.")
    else:
        print("Błędna ścieżka.")
