"""Consumer checks against installed artifacts, including real process locks."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

import locket


class LocketConsumerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="locket-consumer-")
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "lock")

    def test_installed_origin(self):
        root = Path(os.environ["LOCKET_PACKAGE_ROOT"]).resolve()
        self.assertTrue(Path(locket.__file__).resolve().is_relative_to(root))
        self.assertTrue((root / "locket" / "__init__.py").is_file())

    def test_context_releases_lock(self):
        with locket.lock_file(self.path, timeout=0):
            self.assertTrue(Path(self.path).is_file())
        with locket.lock_file(self.path, timeout=0):
            pass

    def test_explicit_acquire_release(self):
        lock = locket.lock_file(self.path, timeout=0)
        lock.acquire()
        lock.release()
        lock.acquire()
        lock.release()

    def test_same_path_is_not_reentrant(self):
        with locket.lock_file(self.path, timeout=0):
            with self.assertRaises(locket.LockError):
                locket.lock_file(self.path, timeout=0).acquire()

    def test_release_unlocked_raises(self):
        with self.assertRaisesRegex(locket.LockError, "cannot release unlocked lock"):
            locket.lock_file(self.path).release()

    def test_exception_releases_lock(self):
        with self.assertRaisesRegex(ValueError, "consumer error"):
            with locket.lock_file(self.path, timeout=0):
                raise ValueError("consumer error")
        with locket.lock_file(self.path, timeout=0):
            pass

    def test_different_paths_are_independent(self):
        with locket.lock_file(self.path, timeout=0):
            with locket.lock_file(self.path + "-other", timeout=0):
                pass

    def test_thread_cannot_acquire_held_lock(self):
        results = []

        def contend():
            try:
                with locket.lock_file(self.path, timeout=0):
                    results.append("acquired")
            except locket.LockError:
                results.append("blocked")

        with locket.lock_file(self.path, timeout=0):
            worker = threading.Thread(target=contend, daemon=True)
            worker.start()
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(results, ["blocked"])

    def test_process_exclusion_and_recovery(self):
        code = (
            "import locket,sys\n"
            "try:\n"
            "    with locket.lock_file(sys.argv[1],timeout=0.1,retry_period=0.01):\n"
            "        print('acquired')\n"
            "except locket.LockError:\n"
            "    print('blocked')\n"
        )
        cmd = [sys.executable, "-c", code, self.path]
        with locket.lock_file(self.path, timeout=0):
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "blocked")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "acquired")

    def test_killed_process_releases_lock(self):
        code = (
            "import locket,sys\n"
            "with locket.lock_file(sys.argv[1]):\n"
            "    print('ready',flush=True)\n"
            "    sys.stdin.readline()\n"
        )
        with tempfile.TemporaryFile(mode="w+") as output:
            process = subprocess.Popen(
                [sys.executable, "-c", code, self.path],
                stdin=subprocess.PIPE, stdout=output, stderr=subprocess.PIPE,
                text=True,
            )
            try:
                import time
                deadline = time.monotonic() + 10
                ready = False
                while time.monotonic() < deadline and process.poll() is None:
                    output.seek(0)
                    if "ready" in output.read():
                        ready = True
                        break
                    time.sleep(0.02)
                self.assertTrue(ready, "child did not acquire lock")
                with self.assertRaises(locket.LockError):
                    locket.lock_file(self.path, timeout=0).acquire()
                process.kill()
                process.communicate(timeout=5)
                self.assertIsNotNone(process.returncode)
                with locket.lock_file(self.path, timeout=0):
                    pass
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
