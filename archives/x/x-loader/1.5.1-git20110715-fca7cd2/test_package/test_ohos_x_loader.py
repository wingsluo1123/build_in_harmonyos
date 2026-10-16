#!/usr/bin/env python3
"""HarmonyOS-only kernel, target and runtime checks for x-loader."""

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

LOAD_ADDR = 0x40200800

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


def command(args, cwd=None):
    result = subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout


def readelf():
    # The CI profile's PATH omits /system/bin, so fall back to a known location.
    return (
        shutil.which("readelf")
        or shutil.which("llvm-readelf")
        or "/data/service/hnp/bin/readelf"
    )


def elf_header(path):
    return command([readelf(), "-h", str(path)])


def main(package_folder):
    root = Path(package_folder)
    signtool = root / "bin" / "signGP"
    firmware = root / "share" / "x-loader"
    mlo = firmware / "MLO"
    raw = firmware / "x-load.bin"
    elf = firmware / "x-load.elf"

    # Query the kernel through Python's uname binding: the CI profile's PATH
    # omits /system/bin, so spawning the uname executable is not reliable.
    kernel = os.uname()
    check(kernel.sysname == "HarmonyOS",
          "test is running on the HarmonyOS kernel")
    check(kernel.machine == "aarch64",
          "device is the expected AArch64 target")

    code, header = elf_header(signtool)
    check(code == 0 and re.search(r"Machine:\s+AArch64", header) is not None,
          "bin/signGP is an AArch64 ELF executable")

    code, program_headers = command([readelf(), "-l", str(signtool)])
    check(code == 0 and "/lib/ld-musl-aarch64.so.1" in program_headers,
          "bin/signGP uses the HarmonyOS musl dynamic loader")

    code, output = command([str(signtool), "--version"])
    check(code == 0 and output.startswith("signGP"),
          "signGP starts on HarmonyOS")

    # The firmware is 32-bit ARM code for the OMAP3530 (Cortex-A8); it must not
    # be confused with an AArch64 host binary.
    code, header = elf_header(elf)
    check(code == 0 and re.search(r"Machine:\s+ARM\b", header) is not None,
          "x-load.elf is a 32-bit ARM executable")
    entry = re.search(r"Entry point address:\s*(0x[0-9a-fA-F]+)", header)
    check(entry is not None and int(entry.group(1), 16) == LOAD_ADDR,
          "x-load.elf entry point is the 0x%08x load address" % LOAD_ADDR)

    # Real content checks on the packaged firmware image.
    signed_bytes = mlo.read_bytes()
    size, load_addr = struct.unpack("<II", signed_bytes[:8])
    check(size == len(raw.read_bytes()),
          "MLO header records the raw image size (%d bytes)" % size)
    check(load_addr == LOAD_ADDR,
          "MLO header records the 0x%08x load address" % LOAD_ADDR)
    reset_vector = struct.unpack("<I", signed_bytes[8:12])[0]
    check(reset_vector >> 24 == 0xEA,
          "MLO payload starts with an ARM branch instruction (reset vector)")

    # Sign the packaged raw image on device and compare with the packaged MLO.
    workdir = tempfile.mkdtemp(prefix="x-loader-ohos-")
    try:
        shutil.copy(str(raw), os.path.join(workdir, "x-load.bin"))
        code, _ = command([str(signtool), "x-load.bin", hex(LOAD_ADDR)], cwd=workdir)
        regenerated = os.path.join(workdir, "x-load.bin.ift")
        check(code == 0 and os.path.isfile(regenerated),
              "signGP signs the OMAP image on HarmonyOS")
        if os.path.isfile(regenerated):
            with open(regenerated, "rb") as handle:
                check(handle.read() == signed_bytes,
                      "on-device signing reproduces the packaged MLO exactly")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("RESULT: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_ohos_x_loader.py <package-folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
