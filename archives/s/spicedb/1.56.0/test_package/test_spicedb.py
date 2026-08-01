#!/usr/bin/env python3
"""Smoke-test the installed spicedb command."""

import pathlib
import subprocess
import sys


def run(command):
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    ).stdout


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: test_spicedb.py <path-to-spicedb>")

    exe = pathlib.Path(sys.argv[1])
    if not exe.is_file():
        raise RuntimeError(f"spicedb executable is missing: {exe}")

    help_output = run([str(exe), "--help"])
    if "spicedb" not in help_output.lower():
        raise RuntimeError("spicedb --help did not identify the command")

    version_output = run([str(exe), "version"])
    if "1.56.0" not in version_output and "spicedb" not in version_output.lower():
        raise RuntimeError(f"Unexpected spicedb version output: {version_output!r}")

    print("spicedb package checks passed: 3/3")


if __name__ == "__main__":
    main()
