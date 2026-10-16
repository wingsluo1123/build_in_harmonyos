#!/usr/bin/env python3
"""Consumer smoke tests for the packaged x-loader bootloader and signGP tool."""

import os
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


def run(args, cwd=None):
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


def main(package_folder):
    root = Path(package_folder)
    signtool = root / "bin" / "signGP"
    firmware = root / "share" / "x-loader"
    mlo = firmware / "MLO"
    raw = firmware / "x-load.bin"
    signed = firmware / "x-load.bin.ift"
    elf = firmware / "x-load.elf"

    artifacts = [signtool, mlo, raw, signed, elf]
    for path in artifacts:
        check(path.is_file(), "packaged file exists: " + str(path))

    if not all(path.is_file() for path in artifacts):
        print("RESULT: %d passed, %d failed" % (passed, failed))
        return 1

    check(os.access(signtool, os.X_OK), "bin/signGP is executable")

    code, output = run([str(signtool), "--version"])
    check(code == 0 and output.startswith("signGP"),
          "signGP --version reports the tool version")

    code, output = run([str(signtool), "--help"])
    check(code == 0 and "Usage: signGP" in output,
          "signGP --help prints its usage")

    # MLO is the flashable name of the signed image.
    signed_bytes = signed.read_bytes()
    check(mlo.read_bytes() == signed_bytes,
          "MLO is identical to the signed image x-load.bin.ift")

    # The TI signed header is <image size (u32 LE)> <load address (u32 LE)>.
    size, load_addr = struct.unpack("<II", signed_bytes[:8])
    check(size == len(raw.read_bytes()),
          "signed header records the raw image size (%d bytes)" % size)
    check(load_addr == LOAD_ADDR,
          "signed header records the 0x%08x load address" % LOAD_ADDR)

    # Re-sign the packaged raw image on this host and compare byte for byte.
    workdir = tempfile.mkdtemp(prefix="x-loader-test-")
    try:
        shutil.copy(str(raw), os.path.join(workdir, "x-load.bin"))
        code, _ = run([str(signtool), "x-load.bin", hex(LOAD_ADDR)], cwd=workdir)
        regenerated = os.path.join(workdir, "x-load.bin.ift")
        check(code == 0 and os.path.isfile(regenerated),
              "signGP signs a raw image in a scratch directory")
        if os.path.isfile(regenerated):
            with open(regenerated, "rb") as handle:
                check(handle.read() == signed_bytes,
                      "regenerated signed image matches the packaged MLO byte for byte")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("RESULT: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_x_loader.py <package-folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
