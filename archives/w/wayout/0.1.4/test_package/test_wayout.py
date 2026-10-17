#!/usr/bin/env python3
"""Consumer smoke tests for the packaged wayout binary."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

VERSION = "0.1.4"

passed = 0
failed = 0


def check(condition, message):
    global passed, failed
    if condition:
        passed += 1
        print("PASS: " + message)
    else:
        failed += 1
        print("FAIL: " + message)


def run(args, cwd=None):
    env = dict(os.environ)
    # No compositor in a container: wayout must fail cleanly instead of hanging.
    env.pop("WAYLAND_DISPLAY", None)
    env.pop("WAYLAND_SOCKET", None)
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout


def readelf():
    return (
        shutil.which("readelf")
        or shutil.which("llvm-readelf")
        or "/data/service/hnp/bin/readelf"
    )


def main(package_folder):
    root = Path(package_folder)
    binary = root / "bin" / "wayout"
    license_file = root / "licenses" / "LICENSE"

    check(binary.is_file(), "packaged file exists: " + str(binary))
    check(license_file.is_file(), "license file is installed")
    if not binary.is_file():
        print("RESULT: %d passed, %d failed" % (passed, failed))
        return 1

    check(os.access(binary, os.X_OK), "bin/wayout is executable")

    code, output = run([str(binary), "--version"])
    check(code == 0, "wayout --version exits successfully")
    check("wayout version " + VERSION in output,
          "wayout --version reports version " + VERSION)

    code, output = run([str(binary), "--help"])
    check(code == 0, "wayout --help exits successfully")
    check("Usage: wayout [options]" in output, "help output prints the usage line")
    check("--feed-line" in output and "--feed-delimiter" in output,
          "help output lists the feed options")

    code, output = run([str(binary), "--definitely-not-an-option"])
    check(code == 1 and "Invalid parameter" in output,
          "an unknown option is rejected with exit code 1")

    code, output = run([str(binary), "--width"])
    check(code == 1 and "Parameter required" in output,
          "an option missing its value is rejected")

    code, output = run([str(binary), "-d", "["])
    check(code == 1 and "invalid regex" in output,
          "an invalid --feed-delimiter regex is reported and aborts")

    code, output = run([str(binary), "--feed-line"])
    check(code == 1 and "Can not connect to a Wayland server" in output,
          "without a compositor wayout exits 1 after a real wl_display_connect")

    code, header = run([readelf(), "-h", str(binary)])
    check(code == 0 and re.search(r"Machine:\s+AArch64", header) is not None,
          "bin/wayout is an AArch64 ELF executable")

    code, dynamic = run([readelf(), "-d", str(binary)])
    needed = re.findall(r"Shared library: \[([^\]]+)\]", dynamic)
    check(code == 0 and "libpangocairo-1.0.so.0" in needed
          and "libcairo.so.2" in needed
          and "libwayland-client.so.0" in needed,
          "wayout dynamically links the pango/cairo/wayland chain")

    print("RESULT: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_wayout.py <package-folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
