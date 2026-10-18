"""Installed-artifact consumers; no network or third-party test runner."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SITE = Path(os.environ["ISBNLIB_PACKAGE_ROOT"]).resolve()
sys.path.insert(0, str(SITE))
import isbnlib


def child(code, *paths):
    bootstrap = "import sys; sys.path[:0] = sys.argv[1:]; "
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", bootstrap + code,
         str(SITE), *map(str, paths)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result


class InstalledIsbnlibTests(unittest.TestCase):
    def test_01_origin(self):
        self.assertEqual(Path(isbnlib.__file__).resolve().relative_to(SITE).parts[0], "isbnlib")
        self.assertEqual(isbnlib.__version__, "3.10.14")

    def test_02_isbn10(self):
        self.assertTrue(isbnlib.is_isbn10("0321534964"))
        self.assertFalse(isbnlib.is_isbn10("0321534965"))

    def test_03_isbn13(self):
        self.assertTrue(isbnlib.is_isbn13("9780321534965"))
        self.assertFalse(isbnlib.is_isbn13("9780321534964"))

    def test_04_conversion(self):
        self.assertEqual(isbnlib.to_isbn13("0321534964"), "9780321534965")
        self.assertEqual(isbnlib.to_isbn10("9780321534965"), "0321534964")
        self.assertEqual(isbnlib.to_isbn10("9791090636071"), "")

    def test_05_canonical(self):
        self.assertEqual(isbnlib.canonical("ISBN 978-0-321-53496-5"), "9780321534965")
        self.assertEqual(isbnlib.canonical("ISBN 0-8044-2957-X"), "080442957X")

    def test_06_checksums(self):
        self.assertEqual(isbnlib.check_digit10("032153496"), "4")
        self.assertEqual(isbnlib.check_digit13("978032153496"), "5")

    def test_07_range_data(self):
        self.assertEqual(isbnlib.mask("9780321534965"), "978-0-321-53496-5")
        self.assertEqual(isbnlib.mask("9791090636071"), "979-10-90636-07-1")

    def test_08_group_info(self):
        self.assertIn("English", isbnlib.info("9780321534965"))

    def test_09_formatter(self):
        from isbnlib.registry import bibformatters
        metadata = {"ISBN-13": "9780321534965", "Title": "Catalogue",
                    "Authors": ["Alex Reader"], "Year": "2023", "Publisher": "Example"}
        self.assertEqual(json.loads(bibformatters["json"](metadata))["title"], "Catalogue")
        self.assertIn("Catalogue", bibformatters["bibtex"](metadata))

    def test_10_registry(self):
        from isbnlib import registry
        original = registry.services["default"]
        try:
            registry.add_service("localtest", lambda value: {"ISBN-13": value})
            registry.setdefaultservice("localtest")
            self.assertEqual(registry.services["default"]("9780321534965"),
                             {"ISBN-13": "9780321534965"})
        finally:
            registry.services["default"] = original
            registry.services.pop("localtest", None)

    def _plugin_directory(self, directory):
        root = Path(directory)
        (root / "catalog_plugin.py").write_text(
            "def query(value):\n    return {'ISBN-13': value, 'Title': 'Plugin book'}\n"
            "formatter = 'JSON'\n", encoding="utf-8")
        dist = root / "catalog_plugin-1.0.dist-info"
        dist.mkdir()
        (dist / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: catalog-plugin\nVersion: 1.0\n", encoding="utf-8")
        (dist / "entry_points.txt").write_text(
            "[isbnlib.metadata]\ncatalogtest = catalog_plugin:query\n"
            "[isbnlib.formatters]\ncatalogfmt = catalog_plugin:formatter\n"
            "[unrelated.group]\nwronggroup = catalog_plugin:query\n", encoding="utf-8")

    def test_11_plugin_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            self._plugin_directory(directory)
            child("import isbnlib.registry as r; "
                  "assert r.services['catalogtest']('9780321534965')['Title'] == 'Plugin book'; "
                  "assert r.bibformatters['catalogfmt'] == 'json'; "
                  "assert 'catalogtest' in r.PROVIDERS and 'catalogfmt' in r.BIBFORMATS; "
                  "assert 'wronggroup' not in r.services; "
                  "assert 'pkg_resources' not in sys.modules", directory)

    def test_12_plugins_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            self._plugin_directory(directory)
            child("from isbnlib.config import options; "
                  "options['LOAD_METADATA_PLUGINS'] = False; "
                  "options['LOAD_FORMATTER_PLUGINS'] = False; "
                  "import isbnlib.registry as r; "
                  "assert 'catalogtest' not in r.services and 'catalogfmt' not in r.bibformatters; "
                  "assert 'goob' in r.services and 'bibtex' in r.bibformatters", directory)

    def test_13_no_plugins(self):
        child("import isbnlib.registry as r; "
              "assert all(name in r.services for name in ['goob', 'openl', 'wiki']); "
              "assert 'pkg_resources' not in sys.modules")

    def test_14_catalogue_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "catalogue.json"
            producer = (
                "import json; from pathlib import Path; import isbnlib; "
                "raw=['ISBN 0-321-53496-4','978-0-321-53496-5','979-10-90636-07-1','bad']; "
                "items=[isbnlib.to_isbn13(isbnlib.canonical(x)) for x in raw]; "
                "items=sorted(set(x for x in items if x and isbnlib.is_isbn13(x))); "
                "Path(sys.argv[2]).write_text(json.dumps(items), encoding='utf-8')"
            )
            child(producer, target)
            consumer = (
                "import json; from pathlib import Path; import isbnlib; "
                "items=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')); "
                "assert items==['9780321534965','9791090636071']; "
                "assert [isbnlib.mask(x) for x in items]=="
                "['978-0-321-53496-5','979-10-90636-07-1']; "
                "assert all(isbnlib.is_isbn13(x) for x in items)"
            )
            child(consumer, target)

    def test_15_spawn_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "catalog_tasks.py").write_text(
                "def square(value):\n    return value * value\n"
                "def fail(value):\n    raise ValueError(value)\n", encoding="utf-8")
            child("import multiprocessing as mp; mp.set_start_method('spawn', force=True); "
                  "from catalog_tasks import square, fail; from isbnlib.dev import vias; "
                  "assert vias.multi((('square', square), ('fail', fail)), 5) == "
                  "{'square': 25, 'fail': None}", directory)


if __name__ == "__main__":
    unittest.main(verbosity=2)
