#!/usr/bin/env python3
"""HarmonyOS-only kernel, ELF and runtime checks for wayout."""

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
    # The CI profile's PATH omits /system/bin; fall back to a known location.
    return (
        shutil.which("readelf")
        or shutil.which("llvm-readelf")
        or "/data/service/hnp/bin/readelf"
    )


def main(package_folder):
    root = Path(package_folder)
    binary = root / "bin" / "wayout"

    # Query the kernel through Python's uname binding (spawning uname is not
    # reliable when /system/bin is not on PATH).
    kernel = os.uname()
    check(kernel.sysname == "HarmonyOS",
          "test is running on the HarmonyOS kernel")
    check(kernel.machine == "aarch64",
          "device is the expected AArch64 target")

    code, header = run([readelf(), "-h", str(binary)])
    check(code == 0 and re.search(r"Class:\s+ELF64", header) is not None,
          "bin/wayout is an ELF64 executable")
    check(code == 0 and re.search(r"Machine:\s+AArch64", header) is not None,
          "bin/wayout is an AArch64 executable")

    code, program_headers = run([readelf(), "-l", str(binary)])
    check(code == 0 and "/lib/ld-musl-aarch64.so.1" in program_headers,
          "bin/wayout uses the HarmonyOS musl dynamic loader")

    # Running on device proves the signed ELF is loadable and every DT_NEEDED
    # library (pango/cairo/wayland from the Conan runtime env) resolves.
    code, version_out = run([str(binary), "--version"])
    check(code == 0, "wayout starts on HarmonyOS")
    check("wayout version " + VERSION in version_out,
          "wayout --version reports " + VERSION + " on device")
    check("Error loading shared library" not in version_out
          and "Error relocating" not in version_out,
          "all dynamic dependencies resolve on device")

    code, help_out = run([str(binary), "--help"])
    check(code == 0 and "Usage: wayout [options]" in help_out,
          "wayout --help prints the usage on device")
    check("--feed-delimiter" in help_out and "--layer" in help_out,
          "help output exposes the feed and layer options")

    # Real libwayland connection attempt (fails because no compositor runs).
    code, no_display = run([str(binary), "--feed-line"])
    check(code == 1 and "Can not connect to a Wayland server" in no_display,
          "wayout performs a real wl_display_connect and reports the missing compositor")
    check("Error relocating" not in no_display,
          "no unresolved symbols when the libwayland client path is exercised")

    code, bad_regex = run([str(binary), "-d", "["])
    check(code == 1 and "invalid regex" in bad_regex,
          "on-device regcomp() rejects an invalid delimiter regex")

    code, dynamic = run([readelf(), "-d", str(binary)])
    needed = re.findall(r"Shared library: \[([^\]]+)\]", dynamic)
    check("libpangocairo-1.0.so.0" in needed
          and "libcairo.so.2" in needed
          and "libwayland-client.so.0" in needed,
          "wayout links the pango/cairo/wayland chain dynamically")

    print("RESULT: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_ohos_wayout.py <package-folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
