"""Consumers exercise the installed package and real child processes."""
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def produce(queue, values):
    import multiprocess
    queue.put((multiprocess.__file__, [v * v for v in values]))


class MultiprocessConsumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("multiprocess") is None:
            raise AssertionError("installed multiprocess package is missing")
        import multiprocess
        cls.mp = multiprocess
        cls.root = Path(os.environ["MULTIPROCESS_PACKAGE_ROOT"]).resolve()

    def test_installed_origin_and_metadata(self):
        self.assertTrue(Path(self.mp.__file__).resolve().is_relative_to(self.root))
        self.assertEqual(self.mp.__version__, "0.70.19")
        self.assertEqual(importlib.metadata.version("multiprocess"), "0.70.19")

    def test_default_context_matches_interpreter_policy(self):
        import multiprocessing
        self.assertEqual(self.mp.get_start_method(), multiprocessing.get_start_method())
        self.assertEqual(self.mp.get_all_start_methods()[0], self.mp.get_start_method())

    def test_import_preserves_stdlib_context_selection(self):
        code = (
            "import multiprocessing as mp; "
            "assert mp.get_start_method(allow_none=True) is None; "
            "import multiprocess; "
            "assert mp.get_start_method(allow_none=True) is None; "
            "mp.set_start_method('spawn'); "
            "assert mp.get_start_method() == 'spawn'"
        )
        subprocess.run([sys.executable, "-s", "-P", "-c", code],
                       cwd=tempfile.gettempdir(), timeout=30, check=True)

    def test_ignore_environment_spawn_bootstrap(self):
        code = (
            "import sys; sys.path[:0] = " + repr(sys.path) + "; "
            "import multiprocess as mp; "
            "p=mp.get_context('spawn').Process(target=print,args=('BOOTSTRAP_OK',)); "
            "p.start(); p.join(15); assert p.exitcode == 0"
        )
        result = subprocess.run([sys.executable, "-B", "-E", "-s", "-P", "-c", code],
                                cwd=tempfile.gettempdir(), timeout=30,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BOOTSTRAP_OK", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_default_listener_roundtrip(self):
        from multiprocess.connection import Client, Listener
        with Listener(authkey=None) as listener:
            client = Client(listener.address, authkey=None)
            server = listener.accept()
            try:
                client.send({"value": [2, 5]})
                self.assertEqual(server.recv(), {"value": [2, 5]})
            finally:
                server.close()
                client.close()

    def test_default_manager_shared_data(self):
        with self.mp.Manager() as manager:
            values = manager.list([4, 9])
            values.append(16)
            self.assertEqual(list(values), [4, 9, 16])

    def test_shared_manager_clean_interpreter_shutdown(self):
        code = (
            "from multiprocess.managers import SharedMemoryManager; "
            "manager=SharedMemoryManager(); manager.start(); "
            "manager.ShareableList([2,3]); manager.shutdown()"
        )
        result = subprocess.run([sys.executable, "-s", "-P", "-c", code],
                                cwd=tempfile.gettempdir(), timeout=30,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_all_start_methods_queue_and_child_origin(self):
        for method in self.mp.get_all_start_methods():
            with self.subTest(method=method):
                ctx = self.mp.get_context(method)
                queue = ctx.Queue()
                child = ctx.Process(target=produce, args=(queue, [2, 3, 5]))
                try:
                    child.start()
                    origin, result = queue.get(timeout=30)
                    child.join(30)
                    self.assertEqual(child.exitcode, 0)
                    self.assertEqual(result, [4, 9, 25])
                    self.assertTrue(Path(origin).resolve().is_relative_to(self.root))
                finally:
                    if child.is_alive():
                        child.terminate()
                        child.join(10)
                    queue.close()
                    queue.join_thread()

    def test_spawn_pool_closure(self):
        offset = 7
        with self.mp.get_context("spawn").Pool(2) as pool:
            self.assertEqual(pool.map(lambda x: x * x + offset, [1, 2, 3]), [8, 11, 16])

    def test_async_error_propagates(self):
        with self.mp.get_context("spawn").Pool(1) as pool:
            result = pool.apply_async(lambda: 1 / 0)
            with self.assertRaises(ZeroDivisionError):
                result.get(timeout=30)

    def test_pipe_dill_callable(self):
        left, right = self.mp.Pipe()
        try:
            left.send(lambda x: x + 11)
            self.assertEqual(right.recv()(4), 15)
        finally:
            left.close()
            right.close()

    def test_shared_memory_lifecycle(self):
        from multiprocess.shared_memory import SharedMemory
        memory = SharedMemory(create=True, size=8)
        try:
            memory.buf[:4] = b"OHOS"
            reader = SharedMemory(name=memory.name)
            try:
                self.assertEqual(bytes(reader.buf[:4]), b"OHOS")
            finally:
                reader.close()
        finally:
            memory.close()
            memory.unlink()

    def test_spawn_shared_value(self):
        ctx = self.mp.get_context("spawn")
        value = ctx.Value("i", 8)
        child = ctx.Process(target=lambda v: setattr(v, "value", v.value + 5), args=(value,))
        try:
            child.start()
            child.join(30)
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(value.value, 13)
        finally:
            if child.is_alive():
                child.terminate()
                child.join(10)

    def test_installed_producer_consumer_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "input.json").write_text('[2,3,5]', encoding="utf-8")
            producer = root / "producer.py"
            producer.write_text(
                "import json,sys\nfrom pathlib import Path\nimport multiprocess as mp\n"
                "if __name__=='__main__':\n"
                "    source=Path(sys.argv[1]); output=Path(sys.argv[2])\n"
                "    with mp.get_context('spawn').Pool(2) as workers:\n"
                "        result=workers.map(lambda x:x*x+7,json.loads(source.read_text()))\n"
                "    output.write_text(json.dumps(result))\n", encoding="utf-8")
            subprocess.run([sys.executable, "-s", str(producer), str(root / "input.json"),
                            str(root / "output.json")], cwd=root, timeout=60, check=True)
            self.assertEqual(json.loads((root / "output.json").read_text()), [11, 16, 32])


if __name__ == "__main__":
    unittest.main(verbosity=2)
