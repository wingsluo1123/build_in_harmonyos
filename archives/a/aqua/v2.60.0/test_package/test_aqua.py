#!/usr/bin/env python3
"""Smoke-test the installed aqua command."""

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
        raise SystemExit("Usage: test_aqua.py <path-to-aqua>")

    exe = pathlib.Path(sys.argv[1])
    if not exe.is_file():
        raise RuntimeError(f"aqua executable is missing: {exe}")

    help_output = run([str(exe), "--help"])
    if "aqua" not in help_output.lower():
        raise RuntimeError("aqua --help did not identify the command")

    version_output = run([str(exe), "version"])
    if "2.60" not in version_output.lower():
        raise RuntimeError(f"Unexpected aqua version output: {version_output!r}")

    print("aqua package checks passed: 3/3")


if __name__ == "__main__":
    main()
