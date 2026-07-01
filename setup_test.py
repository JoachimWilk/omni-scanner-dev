import os

def create_test_env():
    base = "test_lab"
    os.makedirs(f"{base}/wakacje", exist_ok=True)
    os.makedirs(f"{base}/backup/stare", exist_ok=True)

    # 1. Oryginał
    with open(f"{base}/foto1.jpg", "wb") as f:
        f.write(b"to_jest_identyczna_zawartosc_123")

    # 1a. wideo
    with open(f"{base}/wideo1.mov", "wb") as f:
        f.write(b"to_jest_zawartosc_wideo_123")
    
    # 2. Dokładna kopia (inna nazwa, inny folder)
    with open(f"{base}/backup/stare/kopia_foto1.jpg", "wb") as f:
        f.write(b"to_jest_identyczna_zawartosc_123")
    
    # 2a.
    with open(f"{base}/backup/stare/kopia_wideo1.mov", "wb") as f:
        f.write(b"to_jest_zawartosc_wideo_123")

    # 3. Plik o TYM SAMYM ROZMIARZE, ale innej treści (test czujności hasha)
    with open(f"{base}/foto_pomyłka.jpg", "wb") as f:
        f.write(b"to_jest_ZUPELNIE_INNA_zawartosc_!")
    
    # 3a.
    with open(f"{base}/wideo_pomyłka.mov", "wb") as f:
        f.write(b"to_jest_ZUPELNIE_INNA_zawartosc_!")
    
    # 4. unikalne zdjęcia
    with open(f"{base}/wakacje/unikalne.jpg", "wb") as f:
        f.write(b"unikalna_tresc_456789")
    
    # 4a.
    with open(f"{base}/wakacje/unikalny.mov", "wb") as f:
        f.write(b"unikalna_111111_tresc_")
    
    print(f"Struktura testowa stworzona w folderze: {os.path.abspath(base)}")

create_test_env()
