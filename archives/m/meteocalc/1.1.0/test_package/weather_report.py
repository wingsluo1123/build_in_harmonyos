#!/usr/bin/env python3
"""Consumer application: CSV observations -> meteocalc -> JSON report."""
import argparse
import csv
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installed_modules")
    parser.add_argument("observations")
    parser.add_argument("report")
    args = parser.parse_args()
    root = Path(args.installed_modules).resolve()
    sys.path.insert(0, str(root))
    import meteocalc
    from meteocalc import Temp, dew_point, feels_like

    module_path = Path(meteocalc.__file__).resolve()
    if not module_path.is_relative_to(root):
        raise RuntimeError("Consumer imported a module outside the installed package")
    results = []
    # Read and validate all observations before creating the output artifact.
    with open(args.observations, encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            temperature = Temp(float(row["temperature"]), row["unit"])
            humidity = float(row["humidity"])
            wind = float(row["wind_mph"])
            results.append({
                "station": row["station"],
                "temperature_c": temperature.c,
                "dew_point_c": dew_point(temperature, humidity).c,
                "feels_like_f": feels_like(temperature, humidity, wind).f,
            })
    report = {"module": str(module_path), "observations": results}
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, allow_nan=False),
                                 encoding="utf-8")


if __name__ == "__main__":
    main()
