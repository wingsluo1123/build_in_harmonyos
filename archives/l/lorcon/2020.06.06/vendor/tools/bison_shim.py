#!/usr/bin/env python3
"""Replay shim for bison when building vendored libpcap without generators.

Upstream libpcap 1.10.6 ships only scanner.l / grammar.y.in; both its
Autotools configure (AC_CHECK_PROGS + `$BISON_BYACC -V` version parse
selecting %define api.pure) and its CMake build (find_program
FATAL_ERROR) hard-require a working bison, which the HMBS preflight
worker does not provide.  This shim is NOT a fake bison: it replays
byte-exact outputs produced offline by real GNU Bison 3.8.2
(winflexbison v2.5.25, same version as the conancenter bison/3.8.2
toolchain) from this exact upstream tag's grammar.y (grammar.y.in with
@REENTRANT_PARSER@ -> %define api.pure, the value configure itself
selects for bison >= 2.4) with upstream's own flags (-p pcap_ -o -d).
The replayed files live in ../pcap_gen/ and are committed to the recipe.

Invocation: this file is called through the BISON_BYACC /
YACC_EXECUTABLE slot as `python3 bison_shim.py <bison args>` (see
conanfile.py), so it never needs an executable bit (HMBS worker fs
lacks chmod):
  * `-V` / `--version`     -> print a GNU Bison 3.8.2 version banner
                              (parsed by configure/CMake), exit 0
  * `-o OUT [-d [--defines=H]]`
                           -> write committed grammar.c to OUT and
                              committed grammar.h next to it, exit 0
"""

import os
import sys

GEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "pcap_gen")

BISON_VERSION_BANNER = """\
bison (GNU Bison) 3.8.2
Written by Robert Corbett and Richard Stallman.

Copyright (C) 2021 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
"""


def _read(name):
    with open(os.path.join(GEN_DIR, name), "rb") as handle:
        return handle.read()


def _write(path, data):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def main(argv):
    if any(a in ("-V", "--version") for a in argv):
        sys.stdout.write(BISON_VERSION_BANNER)
        return 0
    out = None
    header = None
    want_header = False
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "-o" and idx + 1 < len(argv):
            out = argv[idx + 1]
            idx += 2
        elif arg.startswith("-o") and len(arg) > 2:
            out = arg[2:]
            idx += 1
        elif arg == "-d":
            want_header = True
            idx += 1
        elif arg == "--defines" and idx + 1 < len(argv):
            header = argv[idx + 1]
            want_header = True
            idx += 2
        elif arg.startswith("--defines="):
            header = arg.split("=", 1)[1]
            want_header = True
            idx += 1
        else:
            idx += 1
    if out is None:
        out = os.path.join(os.getcwd(), "grammar.c")
    if want_header and header is None:
        base = os.path.basename(out)
        if "." in base:
            base = base.rsplit(".", 1)[0] + ".h"
        else:
            base = base + ".h"
        header = os.path.join(os.path.dirname(os.path.abspath(out)), base)
    _write(out, _read("grammar.c"))
    if header is not None:
        _write(header, _read("grammar.h"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
