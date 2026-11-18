import unittest

from omniscanner.grouping import analyze_path, build_group
from omniscanner.models import Action, FileInfo


def fi(path, mtime=0):
    return FileInfo(path, 10, mtime)


class KeeperTests(unittest.TestCase):
    def test_exactly_one_keeper_even_if_all_paths_look_like_junk(self):
        """Regresja: stara wersja oznaczała 'DO USUNIĘCIA' wszystkie kopie naraz."""
        g = build_group("d", 10, [
            fi("C:/Users/Jan/Desktop/foto.jpg"),
            fi("C:/Users/Jan/Pulpit/archiwum/foto.jpg"),
            fi("C:/Users/Jan/Downloads/foto.jpg"),
        ])
        self.assertEqual(sum(e.action is Action.KEEP for e in g.entries), 1)
        self.assertEqual(g.entries[0].action, Action.KEEP)

    def test_no_false_positives_from_substrings(self):
        for path in ("D:/Rodzina/Templates_wesele/IMG_1.jpg", "D:/Prawa/Copyright/logo.png",
                     "D:/Zdjecia/Contemporary_art/obraz.jpg", "D:/Zdjecia/Attempt/x.jpg"):
            junk, copy_name = analyze_path(path)
            self.assertEqual((junk, copy_name), ([], False), path)

    def test_detects_real_copies(self):
        self.assertTrue(analyze_path("D:/a/kopia_foto1.jpg")[1])
        self.assertTrue(analyze_path("D:/a/foto - Copy.jpg")[1])
        self.assertTrue(analyze_path("D:/a/foto (1).jpg")[1])
        self.assertEqual(analyze_path("C:\\Users\\X\\Desktop\\a.jpg")[0], ["Desktop"])

    def test_clean_path_beats_junk_path(self):
        g = build_group("d", 10, [
            fi("C:/Users/X/Desktop/foto.jpg", mtime=1),
            fi("D:/Rodzina/Wakacje/foto.jpg", mtime=999),
            fi("D:/Rodzina/Wakacje/kopia_foto.jpg", mtime=1),
        ])
        self.assertEqual(g.keeper.file.path, "D:/Rodzina/Wakacje/foto.jpg")

    def test_oldest_wins_when_paths_equally_clean(self):
        g = build_group("d", 10, [fi("D:/a/x.jpg", mtime=500), fi("D:/b/x.jpg", mtime=100)])
        self.assertEqual(g.keeper.file.path, "D:/b/x.jpg")


if __name__ == "__main__":
    unittest.main()
