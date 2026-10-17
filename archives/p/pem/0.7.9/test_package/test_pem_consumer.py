#!/usr/bin/env python3
"""End-to-end consumer flow for the installed pem command."""
from __future__ import annotations

import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    pem = shutil.which("pem")
    require(pem is not None, "pem executable was not found on PATH")

    with tempfile.TemporaryDirectory() as temp_dir:
        env = dict(os.environ)
        env["HOME"] = temp_dir

        def run(*args: str) -> str:
            result = subprocess.run(
                [pem, *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            return result.stdout

        version = run("--version")
        require("Pem 0.7.9" in version, "unexpected pem version output")

        run("-e", "salary", "1000")
        run("-c", "food", "lunch", "20")

        records = sorted(Path(temp_dir).glob(".pem/*/*"))
        require(len(records) == 1, "expected one persisted pem CSV file")
        with records[0].open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))

        require(len(rows) == 2, "expected two persisted records")
        require(rows[0][1] == "salary", "income description was not persisted")
        require(rows[0][2] == "1000.00", "income amount was not persisted")
        require(rows[1][1] == "lunch", "expense description was not persisted")
        require(rows[1][3] == "20.00", "expense amount was not persisted")
        require(rows[1][4] == "food", "expense category was not persisted")

        daily = run("-s")
        require("salary" in daily and "1000.00" in daily, "daily income report failed")
        require("lunch" in daily and "20.00" in daily, "daily expense report failed")

        monthly = run("-m")
        require("1000.00" in monthly, "monthly income report failed")
        require("20.00" in monthly, "monthly expense report failed")

        category = run("-C")
        require("food" in category, "category report failed")
        require("20.00" in category, "category amount report failed")

    print("[test] pem end-to-end consumer flow passed")


if __name__ == "__main__":
    main()
