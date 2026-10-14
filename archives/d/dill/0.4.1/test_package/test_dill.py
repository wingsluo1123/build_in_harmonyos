"""Installed dill consumer checks, independent of the upstream source tree."""
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest


class DillConsumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.find_spec("dill")
        if spec is None:
            raise AssertionError("installed dill package is missing")
        import dill
        cls.dill = dill
        cls.root = Path(os.environ["DILL_PACKAGE_ROOT"]).resolve()

    def test_installed_origin(self):
        self.assertTrue(Path(self.dill.__file__).resolve().is_relative_to(self.root))
        self.assertEqual(self.dill.__version__, "0.4.1")

    def test_data_protocols(self):
        data = {"文本": [1, 2, None], "bytes": b"\x00\xff"}
        for protocol in range(self.dill.HIGHEST_PROTOCOL + 1):
            self.assertEqual(self.dill.loads(self.dill.dumps(data, protocol=protocol)), data)

    def test_lambda(self):
        self.assertEqual(self.dill.copy(lambda x: x * x)(7), 49)

    def test_closure(self):
        def factory(offset):
            return lambda value: value + offset
        self.assertEqual(self.dill.copy(factory(13))(4), 17)

    def test_dynamic_class(self):
        class Record:
            def __init__(self, value):
                self.value = value
            def double(self):
                return self.value * 2
        self.assertEqual(self.dill.copy(Record(6)).double(), 12)

    def test_recursive_aliases(self):
        node = []
        node.append(node)
        copied = self.dill.copy([node, node])
        self.assertIs(copied[0], copied[1])
        self.assertIs(copied[0][0], copied[0])

    def test_stream(self):
        stream = io.BytesIO()
        self.dill.dump({"x": 7}, stream)
        stream.seek(0)
        self.assertEqual(self.dill.load(stream), {"x": 7})

    def test_file_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("HarmonyOS dill", encoding="utf-8")
            with path.open(encoding="utf-8") as source:
                payload = self.dill.dumps(source, fmode=self.dill.FILE_FMODE)
            restored = self.dill.loads(payload)
            try:
                self.assertEqual(restored.read(), "HarmonyOS dill")
            finally:
                restored.close()

    def test_module_session(self):
        module = types.ModuleType("consumer_session")
        module.value = [3, 4]
        module.function = lambda x: x + 5
        stream = io.BytesIO()
        self.dill.dump_module(stream, module=module)
        stream.seek(0)
        loaded = self.dill.load_module(stream)
        self.assertEqual(loaded.value, [3, 4])
        self.assertEqual(loaded.function(8), 13)

    def test_fresh_interpreter(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = Path(directory) / "function.pkl"
            payload.write_bytes(self.dill.dumps(lambda x: x + 19))
            code = "import dill,sys; from pathlib import Path; assert Path(dill.__file__).resolve().is_relative_to(Path(sys.argv[2]).resolve()); assert dill.load(open(sys.argv[1],'rb'))(4)==23"
            safe_path = ["-P"] if sys.version_info >= (3, 11) else []
            subprocess.run([sys.executable, "-s", *safe_path, "-c", code, str(payload), str(self.root)], cwd=directory, check=True)

    def test_temp_roundtrip(self):
        from dill.temp import dumpIO, loadIO
        self.assertEqual(loadIO(dumpIO(["temporary", 8])), ["temporary", 8])

    def test_source(self):
        from dill.source import getsource
        self.assertIn("def test_source", getsource(self.test_source))

    def test_undill_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = Path(directory) / "data.pkl"
            payload.write_bytes(self.dill.dumps(["hello", "world"]))
            result = subprocess.run([shutil.which("undill"), str(payload)],cwd=directory,check=True,capture_output=True,text=True)
            self.assertEqual(result.stdout.strip(), "['hello', 'world']")

    def test_cli_help(self):
        for name in ("undill", "get_objgraph", "get_gprof"):
            result = subprocess.run([shutil.which(name), "--help"],check=True,capture_output=True,text=True)
            self.assertIn(name, result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
