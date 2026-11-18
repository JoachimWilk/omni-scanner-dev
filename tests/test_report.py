import json
import os
import re
import unittest

from omniscanner.cli import main, normalize_path
from omniscanner.config import parse_size
from omniscanner.core import run_scan
from omniscanner.report import build_data, write_csv, write_html, write_json
from tests.helpers import TmpCase

IMG = frozenset({".jpg"})


def extract_payload(html):
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


class ReportTests(TmpCase):
    def test_hostile_filenames_do_not_inject_html(self):
        names = ['a"b.jpg', "x&y<i>.jpg", "</script><b>.jpg", "ok.jpg"]
        for n in names:
            try:
                self.make(f"in/{n}", b"z" * 300)
            except OSError:
                self.skipTest("system plików odrzuca takie nazwy")
        r = run_scan(str(self.root), IMG)
        data = build_data(r, str(self.root), "test")
        out = self.root.parent / (self.root.name + "_r.html")
        self.addCleanup(lambda: out.exists() and out.unlink())
        write_html(out, data)
        html = out.read_text(encoding="utf-8")
        body = html.split('<script id="data"')[1].split("</script>")[0]
        self.assertNotIn("<i>", body)
        self.assertNotIn("<b>", body)
        self.assertEqual(html.count("</script>"), 2)          # nikt nie zamknął tagu wcześniej
        paths = [e["path"] for e in extract_payload(html)["groups"][0]["entries"]]
        self.assertEqual(len(paths), 4)

    @unittest.skipIf(os.name == "nt", "surrogateescape dotyczy POSIX")
    def test_non_utf8_filename_does_not_crash_report(self):
        base = os.fsencode(str(self.root))
        for n in (b"zly_\xff_nazwa.jpg", b"ok.jpg"):
            with open(os.path.join(base, n), "wb") as f:
                f.write(b"q" * 200)
        r = run_scan(str(self.root), IMG)
        data = build_data(r, str(self.root), "test")
        h, j, c = (self.root.parent / (self.root.name + s) for s in ("_r.html", "_r.json", "_r.csv"))
        self.addCleanup(lambda: [p.unlink() for p in (h, j, c) if p.exists()])
        write_html(h, data); write_json(j, data); write_csv(c, data)   # nie wolno rzucić wyjątku
        self.assertTrue(h.stat().st_size > 0)

    def test_cli_end_to_end_non_interactive(self):
        self.make("a/foto.jpg", b"x" * 2048)
        self.make("b/kopia_foto.jpg", b"x" * 2048)
        out = self.root.parent / (self.root.name + "_out")
        rc = main(["--mode", "1", "--path", str(self.root), "--out", str(out), "--csv"])
        self.addCleanup(lambda: __import__("shutil").rmtree(out, ignore_errors=True))
        self.assertEqual(rc, 0)
        files = sorted(p.suffix for p in out.iterdir())
        for ext in (".html", ".json", ".csv"):
            self.assertIn(ext, files)
        data = json.loads(next(out.glob("wyniki_*.json")).read_text())
        self.assertEqual(data["summary"]["groups"], 1)
        actions = [e["action"] for e in data["groups"][0]["entries"]]
        self.assertEqual(sorted(actions), ["copy", "keep"])

    def test_cli_bad_path_returns_error(self):
        self.assertEqual(main(["--mode", "1", "--path", str(self.root / "nie_ma"),
                               "--out", str(self.root / "o")]), 1)


class UtilTests(unittest.TestCase):
    def test_parse_size(self):
        self.assertEqual(parse_size("1"), 1)
        self.assertEqual(parse_size("10K"), 10 * 1024)
        self.assertEqual(parse_size("5m"), 5 * 1024 ** 2)
        self.assertEqual(parse_size("1.5G"), int(1.5 * 1024 ** 3))
        with self.assertRaises(ValueError):
            parse_size("abc")

    def test_normalize_path_strips_quotes(self):
        self.assertTrue(normalize_path('  "/tmp"  ').endswith("tmp"))


if __name__ == "__main__":
    unittest.main()
