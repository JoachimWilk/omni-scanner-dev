"""OmniScanner – bezpieczny audyt duplikatów zdjęć, wideo i dokumentów."""
import logging

__version__ = "1.5.0"

# Biblioteka nie wypisuje ostrzeżeń na stderr, dopóki aplikacja nie skonfiguruje logowania.
logging.getLogger("omniscanner").addHandler(logging.NullHandler())
