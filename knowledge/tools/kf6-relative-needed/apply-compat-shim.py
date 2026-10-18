#!/usr/bin/env python3
"""Materialise the runtime mirror tree needed by relative DT_NEEDED entries.

The musl loader resolves ``DT_NEEDED`` entries that contain a ``/`` verbatim
against the process working directory.  When a dependency package was linked
without SONAME its entries look like ``../../bin/libKF6ConfigCore.so``; running
from ``<build>/autotests`` therefore requires ``<build>/../bin/libKF6ConfigCore.so``
to exist.  This script creates exactly those paths as symlinks (or copies with
``--copy``), pointing at the real library found in the scanned package roots.

Usage
-----
    # dry run: print what would be created
    ./apply-compat-shim.py --pkg-root "$PKG" --runtime-dir "$BUILD/autotests"

    # create the links
    ./apply-compat-shim.py --pkg-root "$PKG" --runtime-dir "$BUILD/autotests" --apply

    # copy instead of symlink (read-only / no-symlink hosts)
    ./apply-compat-shim.py --pkg-root "$PKG" --runtime-dir "$BUILD/autotests" \
        --apply --copy

Exit codes: 0 = ok (nothing to do or shims in place), 2 = a needed library could
not be located in the given package roots.  ``HMDFS`` ignores ``ln -sf``
overwrite, so existing paths are removed first (R5).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys


def _load_detect():
    """Import the sibling detect script despite its dash in the file name."""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "detect-relative-needed.py")
    spec = importlib.util.spec_from_file_location("relative_needed_detect", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Create the runtime mirror tree for relative DT_NEEDED entries.")
    parser.add_argument("--pkg-root", action="append", required=True,
                        help="package folder holding the real libraries (repeatable)")
    parser.add_argument("--runtime-dir", action="append", required=True,
                        help="directory the binary runs from (repeatable)")
    parser.add_argument("--apply", action="store_true", help="actually create the links")
    parser.add_argument("--copy", action="store_true", help="copy instead of symlink")
    parser.add_argument("--readelf", help="readelf/llvm-readelf to use")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    module = _load_detect()
    report = module.scan(args.pkg_root, args.runtime_dir,
                         module.find_readelf(args.readelf))

    index = {}
    for root in args.pkg_root:
        for lib in module.walk_libs(root):
            index.setdefault(os.path.basename(lib), lib)

    actions, missing = [], []
    for item in report["runtime"]:
        expected = item["expected"]
        if item["present"]:
            actions.append({"path": expected, "action": "exists"})
            continue
        source = index.get(os.path.basename(item["needed"]))
        if not source:
            missing.append({"needed": item["needed"], "expected": expected})
            continue
        actions.append({"path": expected, "action": "link", "source": source})
        if not args.apply:
            continue
        parent = os.path.dirname(expected)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if os.path.lexists(expected):
            os.remove(expected)
        if args.copy:
            shutil.copy2(source, expected)
        else:
            os.symlink(os.path.relpath(source, parent or "."), expected)

    if args.json:
        import json
        print(json.dumps({"actions": actions, "missing": missing}, indent=2))
    else:
        for act in actions:
            if act["action"] == "exists":
                print("ok      %s" % act["path"])
            else:
                print("%-7s %s -> %s" % ("link" if args.apply else "would",
                                         act["path"], act["source"]))
        for item in missing:
            print("MISSING %s (no library named %s in the given roots)"
                  % (item["expected"], os.path.basename(item["needed"])))
        print("summary: %d entr(y/ies), %d link(s) %s, %d unresolved"
              % (len(actions), sum(1 for a in actions if a["action"] == "link"),
                 "created" if args.apply else "planned", len(missing)))
    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
