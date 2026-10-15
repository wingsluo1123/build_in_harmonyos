"""Ten integration cases and one cross-process installed-package workflow."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import plyvel


class InstalledPlyvelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "db")
        self.db = plyvel.DB(self.path, create_if_missing=True)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_01_installed_origin(self):
        root = Path(os.environ["PLYVEL_PACKAGE_ROOT"]).resolve()
        self.assertTrue(Path(plyvel.__file__).resolve().is_relative_to(root))
        self.assertEqual(plyvel.__version__, "1.5.1")
        self.assertEqual(plyvel.__leveldb_version__, "1.23")

    def test_02_binary_roundtrip(self):
        self.db.put(b"a\x00", b"v\x00\xff")
        self.assertEqual(self.db.get(b"a\x00"), b"v\x00\xff")

    def test_03_delete(self):
        self.db.put(b"a", b"v")
        self.db.delete(b"a")
        self.assertIsNone(self.db.get(b"a"))

    def test_04_batch_commit(self):
        with self.db.write_batch() as batch:
            batch.put(b"a", b"1")
            batch.put(b"b", b"2")
        self.assertEqual(list(self.db), [(b"a", b"1"), (b"b", b"2")])

    def test_05_batch_rollback(self):
        with self.assertRaises(ValueError):
            with self.db.write_batch(transaction=True) as batch:
                batch.put(b"a", b"bad")
                raise ValueError("rollback")
        self.assertIsNone(self.db.get(b"a"))

    def test_06_snapshot(self):
        self.db.put(b"a", b"old")
        with self.db.snapshot() as snapshot:
            self.db.put(b"a", b"new")
            self.assertEqual(snapshot.get(b"a"), b"old")
        self.assertEqual(self.db.get(b"a"), b"new")

    def test_07_iterator(self):
        for key in (b"c", b"a", b"b"):
            self.db.put(key, key)
        self.assertEqual(list(self.db.iterator(start=b"b", stop=b"d", reverse=True)),
                         [(b"c", b"c"), (b"b", b"b")])

    def test_08_prefix(self):
        prefixed = self.db.prefixed_db(b"p:")
        prefixed.put(b"a", b"v")
        self.assertEqual(self.db.get(b"p:a"), b"v")
        self.assertEqual(list(prefixed), [(b"a", b"v")])

    def test_09_persistence(self):
        self.db.put(b"a", b"persisted", sync=True)
        self.db.close()
        self.db = plyvel.DB(self.path)
        self.assertEqual(self.db.get(b"a"), b"persisted")

    def test_10_comparator(self):
        def compare(a, b):
            return (a.lower() > b.lower()) - (a.lower() < b.lower())
        with plyvel.DB(os.path.join(self.temp.name, "custom"), create_if_missing=True,
                       comparator=compare, comparator_name=b"casefold-v1") as db:
            db.put(b"b", b"2")
            db.put(b"A", b"1")
            self.assertEqual(list(db), [(b"A", b"1"), (b"b", b"2")])

    def test_11_consumer_workflow(self):
        worker = Path(__file__).with_name("consumer_workflow.py")
        path = os.path.join(self.temp.name, "consumer-db")
        results = []
        for phase in ("write", "read"):
            result = subprocess.run([sys.executable, str(worker), phase, path],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            results.append(json.loads(result.stdout))
        self.assertNotEqual(results[0]["pid"], results[1]["pid"])
        self.assertEqual(results[1]["records"], [["001", "21"], ["002", "19"]])
        self.assertEqual(results[1]["total"], 40)
        print("consumer_workflow: " + json.dumps(results), flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
