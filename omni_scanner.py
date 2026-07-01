import os
import hashlib
import csv
import time
from collections import defaultdict

# --- KONFIGURACJA ---
CHUNK_SIZE = 65536 
LARGE_FILE_THRESHOLD = 1024 * 1024 * 100 # 100MB
SESSION_ID = time.strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = "omniscanner_reports"

PHOTO_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.raw', '.cr2', '.nef', '.arw', '.dng', '.tiff'}
DOCS_EXT = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.txt', '.odt', '.rtf'}
VIDEO_EXT = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.mpeg', '.mpg', '.3gp', '.m4v'}

# --- FUNKCJE POMOCNICZE ---

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def log_error(message):
    ensure_output_dir()
    log_file = os.path.join(OUTPUT_DIR, f"error_{SESSION_ID}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")

def get_file_type(ext):
    if ext in PHOTO_EXT: return "ZDJĘCIE"
    if ext in DOCS_EXT: return "DOKUMENT"
    if ext in VIDEO_EXT: return "WIDEO"
    return "INNY"

def get_action_suggestion(path):
    path_lower = path.lower()
    trash_triggers = ['temp', 'tmp', 'downloads', 'pobrane', 'desktop', 'pulpit', 'copy', 'kopia']
    if any(trigger in path_lower for trigger in trash_triggers):
        return "DO USUNIĘCIA"
    return "ZACHOWAJ (ORYGINAŁ?)"

# --- SILNIK HASHUJĄCY ---

def calculate_fast_hash(file_path):
    try:
        size = os.path.getsize(file_path)
        if size < LARGE_FILE_THRESHOLD:
            return calculate_sha256(file_path)
        with open(file_path, 'rb') as f:
            start_chunk = f.read(CHUNK_SIZE)
            f.seek(-CHUNK_SIZE, os.SEEK_END)
            end_chunk = f.read(CHUNK_SIZE)
            return hashlib.sha256(start_chunk + end_chunk).hexdigest() + "_fast"
    except Exception as e:
        log_error(f"Błąd Fast-Hash: {file_path} | {e}")
        return None

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                sha256.update(chunk)
            return sha256.hexdigest()
    except Exception as e:
        log_error(f"Błąd SHA256: {file_path} | {e}")
        return None

# --- RAPORTOWANIE ---

def save_html_report(results, total_wasted, filename):
    wasted_gb = round(total_wasted / (1024**3), 2)
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <title>OmniScanner v1.4 - Raport Grupowy</title>
        <style>
            :root {{
                --primary: #2563eb;
                --bg: #f1f5f9;
                --text: #1e293b;
                --danger: #ef4444;
                --success: #22c55e;
                --warning: #f59e0b;
            }}
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); padding: 20px; line-height: 1.5; }}
            .container {{ max-width: 1300px; margin: 0 auto; }}
            
            .header {{ background: white; padding: 20px 30px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; border-left: 6px solid var(--primary); }}
            h1 {{ margin: 0; font-size: 20px; text-transform: uppercase; letter-spacing: 1px; }}
            .stats-top {{ display: flex; gap: 20px; }}
            .stat-badge {{ background: #f8fafc; padding: 8px 15px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 13px; }}
            .stat-badge b {{ color: var(--primary); }}

            .controls {{ margin-bottom: 20px; display: flex; gap: 10px; background: white; padding: 12px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); position: sticky; top: 10px; z-index: 100; }}
            button {{ padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: 0.2s; background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }}
            button:hover {{ background: #e2e8f0; }}
            button.active {{ background: var(--primary); color: white; border-color: var(--primary); }}
            button.btn-gigant {{ border-color: var(--warning); color: var(--warning); }}

            .dup-card {{ background: white; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 25px; overflow: hidden; border: 1px solid #e2e8f0; }}
            .group-info {{ background: #f8fafc; padding: 10px 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; font-size: 11px; color: #64748b; font-weight: bold; text-transform: uppercase; }}
            
            table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
            th {{ text-align: left; padding: 12px 20px; font-size: 11px; color: #94a3b8; text-transform: uppercase; background: #fafafa; }}
            td {{ padding: 14px 20px; border-bottom: 1px solid #f1f5f9; font-size: 14px; vertical-align: middle; }}
            
            .col-type {{ width: 100px; }}
            .col-info {{ width: 22%; }}
            .col-sug {{ width: 150px; }}

            /* Nowy układ kolumny ścieżki */
            .path-wrapper {{ display: flex; justify-content: space-between; align-items: center; gap: 15px; }}
            .path-text {{ font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; color: #475569; word-break: break-all; line-height: 1.2; }}
            .copy-btn {{ 
                background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;
                padding: 5px 10px; border-radius: 4px; cursor: pointer;
                font-size: 10px; font-weight: bold; white-space: nowrap;
                transition: 0.2s; flex-shrink: 0;
            }}
            .copy-btn:hover {{ background: var(--primary); color: white; }}
            .copy-success {{ background: var(--success) !important; color: white !important; border-color: var(--success) !important; }}

            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 800; }}
            .type-ZDJĘCIE {{ background: #dbeafe; color: #1e40af; }}
            .type-WIDEO {{ background: #fce7f3; color: #9d174d; }}
            .type-DOKUMENT {{ background: #fef3c7; color: #92400e; }}
            .type-INNY {{ background: #f1f5f9; color: #475569; }}
            .action-DEL {{ background: #fee2e2; color: #b91c1c; }}
            .action-KEEP {{ background: #dcfce7; color: #15803d; }}
            .size-tag {{ color: var(--primary); font-weight: bold; font-size: 11px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>OmniScanner v1.4 <small style="color:#64748b; font-weight:normal;">| Raport</small></h1>
                <div class="stats-top">
                    <div class="stat-badge">Skan: <b>{timestamp}</b></div>
                    <div class="stat-badge">Do odzyskania: <b>{wasted_gb} GB</b></div>
                </div>
            </div>

            <div class="controls">
                <button onclick="filterGroups('all', this)" class="active">Wszystkie</button>
                <button onclick="filterGroups('ZDJĘCIE', this)">Tylko Zdjęcia</button>
                <button onclick="filterGroups('WIDEO', this)">Tylko Wideo</button>
                <button onclick="filterGroups('DOKUMENT', this)">Dokumenty</button>
                <button onclick="filterGroups('DO USUNIĘCIA', this)">Sugestia: Usuń</button>
                <button onclick="filterGroups('GIGANT', this)" class="btn-gigant">⚠️ Giganty (>100MB)</button>
            </div>

            <div id="results-container">
    """

    for h, paths in results.items():
        num_copies = len(paths)
        try: sample_size = round(os.path.getsize(paths[0]) / (1024*1024), 2)
        except: sample_size = 0
        is_gigant_group = "true" if sample_size >= 100 else "false"

        html_content += f"""
        <div class="dup-card" data-gigant="{is_gigant_group}">
            <div class="group-info">
                <span>GRUPA HASH: {h[:12]}...</span>
                <span>ELEMENTY: {num_copies} | ROZMIAR: {sample_size} MB</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th class="col-type">Typ</th>
                        <th class="col-info">Nazwa i Rozmiar</th>
                        <th class="col-sug">Sugestia</th>
                        <th>Pełna Lokalizacja</th>
                    </tr>
                </thead>
                <tbody>
        """
        for p in paths:
            ext = os.path.splitext(p)[1].lower()
            f_type = get_file_type(ext)
            sug = get_action_suggestion(p)
            s_class = "action-DEL" if sug == "DO USUNIĘCIA" else "action-KEEP"
            display_path = p.replace('/', '\\')
            js_path = p.replace('\\', '\\\\').replace("'", "\\'")

            html_content += f"""
                <tr class="file-row" data-type="{f_type}" data-sug="{sug}">
                    <td><span class="badge type-{f_type}">{f_type}</span></td>
                    <td><b>{os.path.basename(p)}</b><br><span class="size-tag">{sample_size} MB</span></td>
                    <td><span class="badge {s_class}">{sug}</span></td>
                    <td>
                        <div class="path-wrapper">
                            <div class="path-text">{display_path}</div>
                            <button class="copy-btn" onclick="copyToClipboard('{js_path}', this)">📋 KOPIUJ</button>
                        </div>
                    </td>
                </tr>
            """
        html_content += "</tbody></table></div>"

    html_content += """
            </div>
        </div>
        <script>
            function copyToClipboard(text, btn) {
                navigator.clipboard.writeText(text).then(() => {
                    const old = btn.innerHTML;
                    btn.innerHTML = "✅ OK!";
                    btn.classList.add('copy-success');
                    setTimeout(() => { btn.innerHTML = old; btn.classList.remove('copy-success'); }, 1500);
                }).catch(() => {
                    const el = document.createElement('textarea');
                    el.value = text; document.body.appendChild(el); el.select();
                    document.execCommand('copy'); document.body.removeChild(el);
                    btn.innerHTML = "✅ OK!"; btn.classList.add('copy-success');
                    setTimeout(() => { btn.innerHTML = "📋 KOPIUJ"; btn.classList.remove('copy-success'); }, 1500);
                });
            }

            function filterGroups(criteria, btn) {
                const groups = document.querySelectorAll('.dup-card');
                const buttons = document.querySelectorAll('.controls button');
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                groups.forEach(group => {
                    const rows = group.querySelectorAll('.file-row');
                    const isGigantGroup = group.getAttribute('data-gigant');
                    let hasVisibleRow = false;

                    rows.forEach(row => {
                        const type = row.getAttribute('data-type');
                        const sug = row.getAttribute('data-sug');
                        let show = (criteria === 'all' || (criteria === 'GIGANT' && isGigantGroup === 'true') || type === criteria || sug === criteria);
                        row.style.display = show ? '' : 'none';
                        if (show) hasVisibleRow = true;
                    });
                    group.style.display = hasVisibleRow ? '' : 'none';
                });
            }
        </script>
    </body>
    </html>
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

# --- GŁÓWNA LOGIKA SKANOWANIA ---

def run_omni_scanner(root_path, choice):
    files_by_size = defaultdict(list)
    print(f"\n[{time.strftime('%H:%M:%S')}] KROK 1: Analiza rozmiarów...")
    
    for dirpath, _, filenames in os.walk(root_path):
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if choice == '1' and ext not in PHOTO_EXT: continue
            if choice == '2' and ext not in (PHOTO_EXT | VIDEO_EXT): continue
            if choice == '3' and ext not in (PHOTO_EXT | DOCS_EXT): continue
            
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
            h = calculate_fast_hash(path)
            if h: temp_hashes[h].append(path)
            processed += 1
            if processed % 10 == 0: print(f" Postęp: {processed}/{num_to_hash}", end='\r')
        
        for h, dup_paths in temp_hashes.items():
            if len(dup_paths) > 1:
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

# --- MAIN ---

if __name__ == "__main__":
    os.system('')
    ensure_output_dir() 

    C_BLUE = '\033[94m'; C_GREEN = '\033[92m'; C_YELLOW = '\033[93m'; C_RED = '\033[91m'; C_BOLD = '\033[1m'; C_END = '\033[0m'

    print(f"\n{C_BLUE}{'='*60}{C_END}")
    print(f"{C_BLUE}{C_BOLD}          OMNI SCANNER v1.4 \"Multimedia Edition\"{C_END}")
    print(f"{C_BLUE}{'='*60}{C_END}")

    print(f"{C_YELLOW}Wybierz zakres skanowania:{C_END}")
    print(f"  {C_BOLD}[1]{C_END} Tylko Zdjęcia")
    print(f"  {C_BOLD}[2]{C_END} Multimedia (Zdjęcia + Wideo)")
    print(f"  {C_BOLD}[3]{C_END} Biuro (Zdjęcia + Dokumenty)")
    print(f"  {C_BOLD}[4]{C_END} Pełny Audyt (Wszystko)")

    choice = input(f"\n{C_BOLD}Wybór:{C_END} ").strip()  
    raw_path = input(f"{C_BOLD}Podaj ścieżkę (np. D: lub C:\\Zdjęcia):{C_END} ").strip()

    path = raw_path.replace('"', '').replace('\\', '/')
    if len(path) == 2 and path.endswith(':'): path += '/'

    if os.path.exists(path):
        start = time.time()
        dups, wasted = run_omni_scanner(path, choice)

        if dups:
            html_name = os.path.join(OUTPUT_DIR, f"raport_{SESSION_ID}.html")
            save_html_report(dups, wasted, html_name)

            print(f"\n{C_GREEN}{'='*60}{C_END}")
            print(f"🏆 {C_BOLD}GOTOWE!{C_END}")
            print(f"Raport: {C_YELLOW}{html_name}{C_END}")
            print(f"Odzyskasz: {C_GREEN}{round(wasted/(1024**3), 2)} GB{C_END} w {round(time.time()-start, 2)}s")
            print(f"{C_GREEN}{'='*60}{C_END}\n")
        else:
            print(f"\n{C_YELLOW}[!] Brak duplikatów.{C_END}")
    else:
        print(f"\n{C_RED}[X] Błędna ścieżka!{C_END}")

    input(f"\n{C_BOLD}Naciśnij Enter, aby zamknąć...{C_END}")