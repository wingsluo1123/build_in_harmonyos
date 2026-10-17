#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile


PACKAGE = sys.argv[1]
BIN = os.path.join(PACKAGE, "bin")


def run(name, args, expected_code=None, expected_text=None):
    path = os.path.join(BIN, name)
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        raise RuntimeError(f"missing executable: {path}")
    result = subprocess.run(
        [path, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
    )
    if expected_code is not None and result.returncode != expected_code:
        raise RuntimeError(f"{name} returned {result.returncode}: {result.stdout}")
    if expected_text and expected_text.lower() not in result.stdout.lower():
        raise RuntimeError(f"{name} output lacks {expected_text!r}: {result.stdout}")
    print(f"PASS {name} {' '.join(args) or '(no args)'}")


run("pbm_findskew", [], expected_code=1, expected_text="usage")
run("tiff_findskew", [], expected_code=1, expected_text="usage")
print("pagetools command consumer tests passed: 2/2")
