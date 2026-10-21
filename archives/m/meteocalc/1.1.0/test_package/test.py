import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE_ROOT = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(PACKAGE_ROOT))

import meteocalc
from meteocalc import Temp, dew_point, feels_like, heat_index, wind_chill


class InstalledPackageTest(unittest.TestCase):
    def test_import_is_installed(self):
        self.assertTrue(Path(meteocalc.__file__).resolve().is_relative_to(PACKAGE_ROOT))

    def test_celsius_fahrenheit(self):
        self.assertAlmostEqual(Temp(0, "c").f, 32)

    def test_kelvin_celsius(self):
        self.assertAlmostEqual(Temp(273.15, "k").c, 0)

    def test_saturation_dew_point(self):
        self.assertAlmostEqual(dew_point(25, 100).c, 25, places=5)

    def test_dew_point_below_temperature(self):
        self.assertLess(dew_point(25, 50).c, 25)

    def test_invalid_humidity(self):
        with self.assertRaises(ValueError):
            dew_point(25, 101)

    def test_wind_chill_known_value(self):
        self.assertAlmostEqual(wind_chill(Temp(0, "f"), 10).f, -15.934471804969, places=5)

    def test_heat_index_known_value(self):
        self.assertAlmostEqual(heat_index(Temp(90, "f"), 70).f, 105.9220206, places=5)

    def test_feels_like_cold_dispatch(self):
        self.assertAlmostEqual(feels_like(Temp(0, "f"), 50, 10).f,
                               wind_chill(Temp(0, "f"), 10).f)

    def test_weather_report_end_to_end(self):
        # Complete installed-package consumer workflow for Conan test_package,
        # runnable on OHOS: actual file I/O, a separate process and errors.
        application = Path(__file__).with_name("weather_report.py")
        with tempfile.TemporaryDirectory(prefix="meteocalc-consumer-") as folder:
            work = Path(folder)
            source = work / "observations.csv"
            report = work / "report.json"
            source.write_text(
                "station,temperature,unit,humidity,wind_mph\n"
                "cold,0,f,50,10\n"
                "hot,90,f,70,0\n"
                "saturated,25,c,100,0\n", encoding="utf-8")
            command = [sys.executable, str(application), str(PACKAGE_ROOT),
                       str(source), str(report)]
            result = subprocess.run(command, cwd=work, capture_output=True,
                                    text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(Path(data["module"]).is_relative_to(PACKAGE_ROOT))
            rows = data["observations"]
            self.assertEqual([row["station"] for row in rows],
                             ["cold", "hot", "saturated"])
            self.assertAlmostEqual(rows[0]["temperature_c"], -17.7777777778, places=6)
            self.assertAlmostEqual(rows[0]["feels_like_f"], -15.934471804969, places=5)
            self.assertAlmostEqual(rows[1]["feels_like_f"], 105.9220206, places=5)
            self.assertAlmostEqual(rows[2]["dew_point_c"], 25, places=5)
            # Invalid humidity must fail rather than emit a successful report.
            report.unlink()
            source.write_text(
                "station,temperature,unit,humidity,wind_mph\n"
                "invalid,25,c,101,0\n", encoding="utf-8")
            failure = subprocess.run(command, cwd=work, capture_output=True,
                                     text=True, timeout=30)
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn("ValueError", failure.stderr)
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
