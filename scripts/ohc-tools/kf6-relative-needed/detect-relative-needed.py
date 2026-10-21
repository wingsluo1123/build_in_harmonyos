#!/usr/bin/env python3
"""Detect library-path DT_NEEDED entries in OHOS dependency packages.

Background
----------
Several published OHOS packages carry shared objects that were linked without
SONAME.  Their ``DT_NEEDED`` therefore keeps the *build-tree relative path*
that the linker saw, e.g.::

    $ readelf -d libKF6ConfigGui.so | grep NEEDED
     0x0000000000000001 (NEEDED)  Shared library: [../../bin/libKF6ConfigCore.so]

The musl loader resolves such an entry verbatim against the *current working
directory* (``LD_LIBRARY_PATH`` does not help), so any consumer that dlopen()s
or executes from a different directory fails with::

    error while loading shared libraries: ../../bin/libKF6ConfigCore.so:
    cannot open shared object file: No such file or directory

This script finds those entries and reports, for every runtime directory of
interest, which mirror paths are missing.  ``apply-compat-shim.py`` builds the
mirror tree that makes them resolvable.

Usage
-----
    # scan one installed package
    ./detect-relative-needed.py --pkg-root "$PKG"

    # scan every lib of the whole dependency graph at once
    ./detect-relative-needed.py --pkg-root "$A" --pkg-root "$B" \
        --runtime-dir "$BUILD_DIR/autotests" --json

    # classify an existing build log instead of binaries
    ./detect-relative-needed.py --log build.log

Exit codes: 0 = clean, 3 = offending entries found, 2 = usage/tool error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

REL_NEEDED_RE = re.compile(r"Shared library: \[(?P<name>[^\]]+)\]")
# musl prints:  Error loading shared library ../../bin/libX.so: (needed by ...)
# glibc prints: error while loading shared libraries: ../../bin/libX.so: cannot
#               open shared object file: No such file or directory
LOG_RE = re.compile(
    r"(?:error loading shared library"
    r"|error while loading shared libraries"
    r"|cannot open shared object file)"
    r"[:\s]+(?P<name>[^\s:]+)", re.IGNORECASE)
# Loader error lines that mention a relative path are the signature we look for.
REL_PATH_HINT = re.compile(r"(?:^|[\s:])(?:\.{1,2}/)+[^\s:]+\.so")


def find_readelf(explicit: str | None) -> list[str]:
    """Candidate readelf implementations, most specific first."""
    if explicit:
        return [explicit]
    candidates = []
    sdk = os.environ.get("OHOS_SDK") or os.environ.get("OHOS_SDK_NATIVE")
    if sdk:
        candidates.append(os.path.join(sdk, "native", "llvm", "bin", "llvm-readelf"))
        candidates.append(os.path.join(sdk, "llvm", "bin", "llvm-readelf"))
    candidates += [
        shutil.which("llvm-readelf") or "",
        shutil.which("readelf") or "",
        shutil.which("llvm-objdump") or "",
    ]
    return [c for c in candidates if c]


def dynamic_needed(path: str, tools: list[str]) -> list[str]:
    """Return the DT_NEEDED entries readelf reports for *path*."""
    if not tools:
        raise SystemExit("no readelf/llvm-readelf found; pass --readelf")
    tool = tools[0]
    if os.path.basename(tool).endswith("objdump"):
        cmd = [tool, "-p", path]
    else:
        cmd = [tool, "-d", path]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except OSError as exc:  # pragma: no cover - environment dependent
        raise SystemExit("cannot run %s: %s" % (tool, exc))
    if out.returncode != 0:
        return []
    return [m.group("name") for m in REL_NEEDED_RE.finditer(out.stdout)]


def walk_libs(root: str):
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if ".so" not in name:
                continue
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            yield full


def required_mirror(runtime_dir: str, needed: str) -> str:
    """Path the loader will look up for a relative *needed* entry."""
    return os.path.normpath(os.path.join(runtime_dir, needed))


def scan(pkg_roots: list[str], runtime_dirs: list[str], tools: list[str]) -> dict:
    report = {"count": 0, "libs": [], "runtime": []}
    for root in pkg_roots:
        for lib in walk_libs(root):
            bad = [n for n in dynamic_needed(lib, tools) if "/" in n]
            if not bad:
                continue
            report["count"] += len(bad)
            report["libs"].append({"lib": lib, "needed": bad})
    for rdir in runtime_dirs:
        for entry in report["libs"]:
            for needed in entry["needed"]:
                target = required_mirror(rdir, needed)
                report["runtime"].append({
                    "runtime_dir": rdir,
                    "needed": needed,
                    "expected": target,
                    "present": os.path.exists(target),
                    "source": entry["lib"],
                })
    return report


def scan_log(path: str) -> dict:
    report = {"count": 0, "hits": []}
    with open(path, "r", errors="replace") as handle:
        for lineno, line in enumerate(handle, 1):
            if not REL_PATH_HINT.search(line):
                continue
            match = LOG_RE.search(line)
            if not match:
                continue
            report["count"] += 1
            report["hits"].append({"line": lineno, "lib": match.group("name"),
                                   "text": line.strip()[:300]})
    return report


def print_text(report: dict, kind: str) -> None:
    if kind == "log":
        for hit in report["hits"]:
            print("RELATIVE-NEEDED  %s:%d  %s" % (hit["line"], 0, hit["lib"]))
            print("    %s" % hit["text"])
        print("total: %d relative library path hit(s)" % report["count"])
        return
    for entry in report["libs"]:
        print("RELATIVE-NEEDED  %s" % entry["lib"])
        for needed in entry["needed"]:
            print("    -> %s" % needed)
    for item in report["runtime"]:
        state = "present" if item["present"] else "MISSING"
        print("%-8s %s  (needed by %s)" % (state, item["expected"],
                                           os.path.basename(item["source"])))
    missing = [i for i in report["runtime"] if not i["present"]]
    print("total: %d relative DT_NEEDED entr(y/ies), %d missing mirror(s)"
          % (report["count"], len(missing)))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Detect DT_NEEDED entries that carry a relative path.")
    parser.add_argument("--pkg-root", action="append", default=[],
                        help="package folder to scan (repeatable)")
    parser.add_argument("--runtime-dir", action="append", default=[],
                        help="directory the binary will run from (repeatable)")
    parser.add_argument("--log", help="classify an existing build log instead")
    parser.add_argument("--readelf", help="readelf/llvm-readelf to use")
    parser.add_argument("--json", action="store_true", help="machine readable output")
    parser.add_argument("--out", help="also write the report to this file")
    args = parser.parse_args(argv)

    if not args.pkg_root and not args.log:
        parser.error("give at least one --pkg-root or --log")

    if args.log:
        report, kind = scan_log(args.log), "log"
        code = 3 if report["count"] else 0
    else:
        tools = find_readelf(args.readelf)
        report = scan(args.pkg_root, args.runtime_dir, tools)
        code = 3 if report["count"] else 0
        kind = "bin"
        report["tools"] = tools

    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.json:
        print(payload)
    else:
        print_text(report, kind)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(payload + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
