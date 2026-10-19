"""Consumer tests for installed utm modules and the bundled command."""
import importlib.metadata
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

PACKAGE = Path(sys.argv.pop(1)).resolve()
import utm


class InstalledUtmTests(unittest.TestCase):
    def test_installed_module_and_metadata(self):
        self.assertEqual(Path(utm.__file__).resolve().parent,
                         PACKAGE / "share" / "utm" / "utm")
        self.assertEqual(utm.__version__, "0.8.1")
        self.assertEqual(importlib.metadata.version("utm"), "0.8.1")

    def test_northern_known_coordinate(self):
        easting, northing, number, letter = utm.from_latlon(50.77535, 6.08389)
        self.assertAlmostEqual(easting, 294409, delta=1)
        self.assertAlmostEqual(northing, 5628898, delta=1)
        self.assertEqual((number, letter), (32, "U"))

    def test_southern_roundtrip(self):
        coordinate = (-41.28646, 174.77624)
        projected = utm.from_latlon(*coordinate)
        self.assertEqual(projected[2:], (60, "G"))
        restored = utm.to_latlon(*projected)
        for actual, expected in zip(restored, coordinate):
            self.assertAlmostEqual(actual, expected, places=5)

    def test_special_zones_and_invalid_input(self):
        self.assertEqual(utm.from_latlon(60, 5)[2], 32)
        self.assertEqual(utm.from_latlon(79, 18)[2], 33)
        with self.assertRaises(utm.OutOfRangeError):
            utm.from_latlon(90, 0)
        with self.assertRaises(utm.OutOfRangeError):
            utm.check_valid_zone(0, "U")

    def test_installed_command_forward_and_inverse(self):
        executable = PACKAGE / "bin" / "utm-converter"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        def command(*args):
            return subprocess.check_output([str(executable), *args], env=env, text=True).strip()
        self.assertEqual(command("--version"), "utm-converter 0.8.1")
        self.assertIn("latlon", command("--help"))
        parts = command("latlon", "50.77535", "6.08389").split(",")
        self.assertEqual(parts[2:], ["32", "U"])
        self.assertTrue(math.isclose(float(parts[0]), 294409, abs_tol=1))
        self.assertTrue(math.isclose(float(parts[1]), 5628898, abs_tol=1))
        latitude, longitude = map(float, command("utm", "294409", "5628898", "32", "U").split(","))
        self.assertAlmostEqual(latitude, 50.77535, delta=0.0001)
        self.assertAlmostEqual(longitude, 6.08389, delta=0.0001)

    def test_command_rejects_invalid_input(self):
        executable = PACKAGE / "bin" / "utm-converter"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        for arguments in (("latlon", "invalid", "6"),
                          ("latlon", "90", "0"),
                          ("utm", "294409", "5628898", "0", "U")):
            with self.subTest(arguments=arguments):
                result = subprocess.run([str(executable), *arguments], env=env,
                                        capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr.strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
