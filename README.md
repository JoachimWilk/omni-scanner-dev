# OmniScanner v1.0 🔍
### Profesjonalny audyt i deduplikacja danych z gwarancją integralności

**OmniScanner** to lekkie, bezpieczne i precyzyjne narzędzie stworzone do porządkowania dużych nośników danych (dyski HDD/SSD do 500GB+). Zamiast polegać na zawodnych nazwach plików, program zagląda do ich "cyfrowego DNA", aby z 100% pewnością wskazać duplikaty.

## 🚀 Główne Tryby Pracy
Program pozwala na wybór głębokości skanowania, co pozwala oszczędzić czas i mechanikę dysku:
1.  **FOTO (1):** Skupienie na zdjęciach i plikach RAW (JPG, PNG, NEF, ARW, DNG itd.).
2.  **SMART (2):** Zdjęcia oraz dokumenty biurowe (PDF, DOCX, XLSX, TXT).
3.  **DEEP (3):** Totalny skan – analizuje każdy plik na nośniku, niezależnie od formatu.

## 🛡 Bezpieczeństwo i Architektura
* **SHA-256 Fingerprinting:** Najwyższy standard bezpieczeństwa – wykrywa duplikaty nawet przy zmienionych nazwach.
* **HDD Optimized:** Odczyt w blokach 64KB (chunking) chroni głowicę dysku przed nadmiernym zużyciem i zapobiega zapchaniu pamięci RAM.
* **Read-Only:** Skrypt nigdy nie usuwa ani nie modyfikuje Twoich plików. Tworzy jedynie raport do Twojej decyzji.
* **Error Tolerance:** Automatycznie pomija pliki systemowe i błędy odczytu (np. uszkodzone sektory), kontynuując pracę.

## 🛠 Instrukcja Obsługi

### 1. Przygotowanie
Upewnij się, że masz zainstalowanego **Pythona 3.x**. Program nie wymaga instalacji żadnych bibliotek (używa tylko `os`, `hashlib`, `csv`).

### 2. Uruchomienie
1. Pobierz plik `omni_scanner.py`.
2. Otwórz terminal w folderze ze skryptem.
3. Wpisz komendę:
   ```bash
   python omni_scanner.py
