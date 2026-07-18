#!/usr/bin/env python3
"""Validate autotrace package layout."""
import os
import sys


pkg = sys.argv[1]
checks = [
    ("autotrace CLI", os.path.join(pkg, "bin", "autotrace")),
    ("autotrace header", os.path.join(pkg, "include", "autotrace", "autotrace.h")),
    ("autotrace library", os.path.join(pkg, "lib", "libautotrace.a")),
    ("autotrace pkgconfig", os.path.join(pkg, "lib", "pkgconfig", "autotrace.pc")),
]

missing = [name for name, path in checks if not os.path.exists(path)]
if missing:
    raise SystemExit("missing autotrace package artifacts: " + ", ".join(missing))

print("PASS: autotrace packaged CLI, headers, static library, and pkg-config metadata")
