"""Run the installed command after relocation in HarmonyOS writable storage."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(sys.argv.pop(1)).resolve()


class HarmonyStorageTests(unittest.TestCase):
    def test_relocated_command_in_harmony_storage(self):
        self.assertEqual(os.uname().sysname, "HarmonyOS")
        self.assertIn(os.uname().machine, ("aarch64", "arm64"))
        storage = Path(os.environ.get("TMPDIR", "/data/storage/el2/base/cache")).resolve()
        self.assertTrue(str(storage).startswith(("/data/storage/", "/storage/")),
                        f"Expected HarmonyOS writable storage, got {storage}")
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        with tempfile.TemporaryDirectory(prefix="utm-ohos-", dir=storage) as temporary:
            relocated = Path(temporary) / "鸿蒙 坐标转换"
            shutil.copytree(PACKAGE, relocated)
            executable = relocated / "bin" / "utm-converter"

            def command(*arguments):
                result = subprocess.run([str(executable), *arguments],
                                        env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                return result.stdout.strip()

            original_directory = Path.cwd()
            try:
                # HarmonyOS Python uses posix_spawn only when cwd is omitted.
                os.chdir(relocated)
                self.assertEqual(command("--version"), "utm-converter 0.8.1")
                projected = command("latlon", "50.77535", "6.08389").split(",")
                self.assertEqual(projected[2:], ["32", "U"])
                self.assertAlmostEqual(float(projected[0]), 294409, delta=1)
                self.assertAlmostEqual(float(projected[1]), 5628898, delta=1)
                # The upstream inverse CLI accepts integer metres.
                inverse = [str(round(float(value))) for value in projected[:2]] + projected[2:]
                restored = list(map(float, command("utm", *inverse).split(",")))
                self.assertEqual(len(restored), 2)
                self.assertAlmostEqual(restored[0], 50.77535, delta=0.0001)
                self.assertAlmostEqual(restored[1], 6.08389, delta=0.0001)
                print(f"HarmonyOS storage relocation verified in {relocated}", flush=True)
            finally:
                os.chdir(original_directory)


if __name__ == "__main__":
    unittest.main(verbosity=2)
