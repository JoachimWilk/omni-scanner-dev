import os
import sys
import unittest

from omniscanner import hashing
from omniscanner.config import PHOTO_EXT, VIDEO_EXT, resolve_mode
from omniscanner.core import run_scan
from tests.helpers import TmpCase

IMG = frozenset({".jpg"})


class PipelineTests(TmpCase):
    def test_identical_copies_form_one_group(self):
        self.make("a/foto.jpg", b"x" * 1000)
        self.make("b/kopia.jpg", b"x" * 1000)
        r = run_scan(str(self.root), IMG)
        self.assertEqual(self.names(r.groups), [["foto.jpg", "kopia.jpg"]])
        self.assertEqual(r.wasted, 1000)

    def test_same_size_different_content_is_not_duplicate(self):
        a, b = b"to_jest_identyczna_zawartosc_123", b"to_jest_ZUPELNIE_INNA_zawartos_!"
        self.assertEqual(len(a), len(b))  # prawdziwy test czujności hasha
        self.make("a.jpg", a)
        self.make("b.jpg", b)
        self.assertEqual(run_scan(str(self.root), IMG).groups, [])

    def test_three_copies_wasted_is_two_sizes(self):
        for n in "abc":
            self.make(f"{n}.jpg", b"z" * 500)
        r = run_scan(str(self.root), IMG)
        self.assertEqual(len(r.groups), 1)
        self.assertEqual(r.wasted, 1000)

    def test_large_files_differing_only_in_unsampled_middle(self):
        """Pliki > 3*SAMPLE: próbki (początek/środek/koniec) są równe, rozstrzyga pełny hash."""
        base = bytearray(os.urandom(400_000))
        other = bytearray(base)
        other[100_000] ^= 0xFF      # poza próbkami (środek to ~200 000 ± 32 768)
        self.make("v1.jpg", bytes(base))
        self.make("v2.jpg", bytes(base))
        self.make("v3.jpg", bytes(other))
        self.assertGreater(400_000, hashing.FULL_ONLY_MAX)
        r = run_scan(str(self.root), IMG)
        self.assertEqual(self.names(r.groups), [["v1.jpg", "v2.jpg"]])

    def test_empty_files_are_ignored(self):
        self.make("a.jpg", b"")
        self.make("b.jpg", b"")
        self.assertEqual(run_scan(str(self.root), IMG).groups, [])

    @unittest.skipUnless(hasattr(os, "link"), "brak twardych linków")
    def test_hardlinks_are_not_duplicates(self):
        a = self.make("a.jpg", b"h" * 2000)
        try:
            os.link(a, self.root / "b.jpg")
        except OSError:
            self.skipTest("system plików nie wspiera twardych linków")
        r = run_scan(str(self.root), IMG)
        self.assertEqual(r.groups, [])
        self.assertEqual(r.stats.hardlinks_skipped, 1)

    def test_mode_filters(self):
        for name in ("a.jpg", "b.jpg", "a.mov", "b.mov", "a.pdf", "b.pdf"):
            self.make(name, b"same-content-" + name[-3:].encode())
        photos = run_scan(str(self.root), resolve_mode("1"))
        multi = run_scan(str(self.root), resolve_mode("2"))
        full = run_scan(str(self.root), resolve_mode("4"))
        self.assertEqual(len(photos.groups), 1)
        self.assertEqual(len(multi.groups), 2)
        self.assertEqual(len(full.groups), 3)

    def test_invalid_mode_raises(self):
        for bad in ("x", "", "5", "0"):
            with self.assertRaises(ValueError):
                resolve_mode(bad)

    def test_excluded_folders_and_output_dir(self):
        self.make("ok/a.jpg", b"q" * 300)
        self.make("node_modules/b.jpg", b"q" * 300)
        out = self.root / "omniscanner_reports"
        self.make("omniscanner_reports/c.jpg", b"q" * 300)
        r = run_scan(str(self.root), IMG, exclude_names={"node_modules"}, skip_paths=[out])
        self.assertEqual(r.groups, [])
        self.assertEqual(r.stats.dirs_excluded, 2)

    def test_symlinks_are_skipped(self):
        a = self.make("a.jpg", b"s" * 300)
        try:
            os.symlink(a, self.root / "link.jpg")
        except (OSError, NotImplementedError):
            self.skipTest("brak symlinków")
        self.assertEqual(run_scan(str(self.root), IMG).groups, [])

    def test_groups_sorted_by_wasted_space_desc(self):
        self.make("s1.jpg", b"a" * 100); self.make("s2.jpg", b"a" * 100)
        self.make("b1.jpg", b"b" * 9000); self.make("b2.jpg", b"b" * 9000)
        r = run_scan(str(self.root), IMG)
        self.assertEqual([g.size for g in r.groups], [9000, 100])

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "wymaga zwykłego użytkownika POSIX")
    def test_unreadable_file_is_reported_not_fatal(self):
        a = self.make("a.jpg", b"u" * 500)
        self.make("b.jpg", b"u" * 500)
        self.make("c.jpg", b"u" * 500)
        os.chmod(a, 0)
        self.addCleanup(os.chmod, a, 0o600)
        r = run_scan(str(self.root), IMG)
        self.assertEqual(r.stats.errors, 1)
        self.assertEqual(len(r.groups), 1)


class CacheTests(TmpCase):
    def test_second_run_does_not_reread_files(self):
        self.make("a.jpg", b"c" * 400_000)
        self.make("b.jpg", b"c" * 400_000)
        db = self.root.parent / (self.root.name + "_cache.sqlite3")
        self.addCleanup(lambda: db.exists() and db.unlink())
        r1 = run_scan(str(self.root), IMG, cache_path=db)
        self.assertEqual(len(r1.groups), 1)

        orig_full, orig_sample = hashing.full_hash, hashing.sample_hash
        hashing.full_hash = lambda *a, **k: self.fail("odczyt pełny mimo cache")
        hashing.sample_hash = lambda *a, **k: self.fail("odczyt próbki mimo cache")
        try:
            r2 = run_scan(str(self.root), IMG, cache_path=db)
        finally:
            hashing.full_hash, hashing.sample_hash = orig_full, orig_sample
        self.assertEqual(len(r2.groups), 1)

    def test_modified_file_invalidates_cache(self):
        a = self.make("a.jpg", b"c" * 1000, mtime=1_000_000)
        self.make("b.jpg", b"c" * 1000, mtime=1_000_000)
        db = self.root.parent / (self.root.name + "_cache2.sqlite3")
        self.addCleanup(lambda: db.exists() and db.unlink())
        self.assertEqual(len(run_scan(str(self.root), IMG, cache_path=db).groups), 1)
        a.write_bytes(b"d" * 1000)                      # ten sam rozmiar, nowa treść
        os.utime(a, (2_000_000, 2_000_000))
        self.assertEqual(run_scan(str(self.root), IMG, cache_path=db).groups, [])


if __name__ == "__main__":
    unittest.main()
