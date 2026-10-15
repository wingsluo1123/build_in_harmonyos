#!/usr/bin/env python3
"""Substantive test for the you-get package (R34).

Runs the packaged bin/you-get launcher with --version and asserts
the output contains the expected upstream version string. This is a
real functional test of the installed console application, not a
print-only placeholder.

Note: `you-get --version` does not import you_get.extractors, so it
does not require dukpy and needs no network access.
"""
import os
import subprocess
import sys

EXPECTED_VERSION = "0.4.1743"


def main():
    pkg_bin = os.environ.get("YOU_GET_BIN")
    if not pkg_bin:
        sys.exit("YOU_GET_BIN environment variable is not set")
    if not os.path.isfile(pkg_bin):
        sys.exit(f"you-get launcher not found: {pkg_bin}")

    proc = subprocess.run([pkg_bin, "--version"],
                          capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    if proc.returncode != 0:
        sys.exit(
            f"you-get --version failed (rc={proc.returncode}):\n{output}")

    assert EXPECTED_VERSION in output, (
        f"expected version string '{EXPECTED_VERSION}' not found "
        f"in you-get --version output:\n{output}")

    print("you-get --version OK (asserted 0.4.1743):")
    print(output)


if __name__ == "__main__":
    main()
