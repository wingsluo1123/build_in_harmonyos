#!/usr/bin/env python3
"""Exercise the packaged xmedcon binaries from a consumer's point of view.

Usage: test_xmedcon.py <path-to-medcon> <path-to-xmedcon>

`medcon` is a pure CLI converter: with no arguments it prints its usage and
exits (MdcPrintUsage), so it is fully runnable headless and proves the whole
libmdc + glib dynamic closure resolves.

`xmedcon` is a GTK+3 GUI: like l3afpad it needs a display, so without one the
meaningful assertions are that the entire GTK+3 shared-library closure
resolves and execution reaches display initialisation before failing.
"""
import os
import struct
import subprocess
import sys


def assert_elf(binary, name):
    assert os.path.isfile(binary), name + " missing: " + binary
    assert os.access(binary, os.X_OK), name + " is not executable"
    with open(binary, "rb") as fh:
        head = fh.read(20)
    assert head[:4] == b"\x7fELF", name + ": not an ELF binary"
    assert head[4] == 2, name + ": not a 64-bit ELF"
    machine = struct.unpack("<H", head[18:20])[0]
    assert machine == 0xB7, "%s: not an aarch64 ELF (e_machine=%#x)" % (name, machine)
    print(name + ": aarch64 ELF verified")


def assert_no_link_errors(text):
    for bad in ("Error loading shared library",
                "symbol not found",
                "undefined symbol",
                "error while loading shared libraries"):
        assert bad not in text, "dynamic link failure: %s" % text


def main():
    medcon, xmedcon = sys.argv[1], sys.argv[2]
    assert_elf(medcon, "medcon")
    assert_elf(xmedcon, "xmedcon")

    # 1) medcon CLI: usage path must run headless and link libmdc+glib.
    result = subprocess.run([medcon], capture_output=True, text=True, timeout=300)
    text = (result.stdout or "") + (result.stderr or "")
    assert_no_link_errors(text)
    assert "medcon" in text.lower(), "medcon usage not printed: %s" % text
    print("medcon usage path OK (headless)")

    # 2) medcon --version style argument must not crash the option parser.
    result = subprocess.run([medcon, "-V"], capture_output=True, text=True, timeout=300)
    text = (result.stdout or "") + (result.stderr or "")
    assert_no_link_errors(text)
    print("medcon -V path OK")

    # 3) xmedcon GUI: full GTK+3 closure resolves; stops at display init only.
    #    GTK emits the lowercase "cannot open display:" warning.
    result = subprocess.run([xmedcon], capture_output=True, text=True, timeout=300)
    text = (result.stdout or "") + (result.stderr or "")
    assert_no_link_errors(text)
    assert "cannot open display" in text.lower(), text
    print("GTK+3 closure resolved; stopped at display init as expected")
    print("XMEDCON-CONSUMER-OK")


main()
