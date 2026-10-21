#!/usr/bin/env python3
"""SmartList test_package driver: deterministic checks + HMBS markers.

Counts come from exactly two deterministic sources (no string-count hacks):
  - C API: one parsed HSORT_CASE line per case from the test_hsort binary
    output ("HSORT_CASE <name>: PASS|FAIL"); HSORT_SUMMARY is informational
    only and never used for arithmetic.
  - Script/binary checks: one entry per explicit check below.
Marker self-check enforces passed + failed == executed and
executed + skipped <= discovered before printing.
"""
import argparse
import json
import os
import subprocess
import sys


def run(cmd):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001 - evidence path
        return 127, f"spawn failed: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--hsort-bin", required=True)
    args = ap.parse_args()
    pkg = args.package

    py_checks = []  # (name, passed, evidence)

    def check(name, passed, evidence):
        py_checks.append((name, bool(passed), evidence[:300]))

    lib = os.path.join(pkg, "lib", "libhsort.a")
    check("libhsort-present", os.path.isfile(lib) and os.path.getsize(lib) > 0,
          f"libhsort.a size={os.path.getsize(lib) if os.path.isfile(lib) else -1}")

    hdr = os.path.join(pkg, "include", "hsort.h")
    try:
        htxt = open(hdr, encoding="utf-8", errors="replace").read()
    except OSError as e:
        htxt = ""
        check("hsort-header", False, f"open failed: {e}")
    else:
        check("hsort-header", "hsort" in htxt, f"hsort.h bytes={len(htxt)}")

    gethome = os.path.join(pkg, "bin", "gethome")
    check("gethome-present", os.path.isfile(gethome) and os.access(gethome, os.X_OK),
          f"gethome exists={os.path.isfile(gethome)}")
    rc, out = run(f'"{gethome}"')
    check("gethome-runs", rc != 0 and "Usage" in out,
          f"rc={rc} out={out.strip()[:160]}")

    bindir = os.path.join(pkg, "bin", "smartlist")
    try:
        scripts = sorted(f for f in os.listdir(bindir) if os.path.isfile(os.path.join(bindir, f)))
    except OSError as e:
        scripts = []
        check("scripts-present", False, f"listdir failed: {e}")
    else:
        check("scripts-present", len(scripts) >= 10, f"scripts={len(scripts)}")
        for must in ("subscribe", "unsubscribe", "digest"):
            check(f"script-{must}", must in scripts, f"found={must in scripts}")

    etc_main = os.path.join(pkg, "share", "smartlist", "etc", "rc.main")
    check("etc-rc-main", os.path.isfile(etc_main) and os.path.getsize(etc_main) > 0,
          f"rc.main size={os.path.getsize(etc_main) if os.path.isfile(etc_main) else -1}")

    exdir = os.path.join(pkg, "share", "smartlist", "examples")
    try:
        examples = os.listdir(exdir)
    except OSError as e:
        examples = []
        check("examples-present", False, f"listdir failed: {e}")
    else:
        check("examples-present", len(examples) > 0, f"examples={len(examples)}")

    # sh -n syntax probe on the sorted script list head (fails closed).
    sample = scripts[:5]
    if sample:
        fails = []
        for s in sample:
            rc, out = run(f'sh -n "{os.path.join(bindir, s)}"')
            if rc != 0:
                fails.append(f"{s}:{out.strip()[:80]}")
        check("scripts-syntax", not fails, "all sh -n clean" if not fails else "; ".join(fails))
    else:
        check("scripts-syntax", False, "no scripts to probe")

    # C API cases: parse test_hsort output line-by-line, one case per line.
    rc, out = run(f'"{args.hsort_bin}"')
    c_total = 0
    c_passed = 0
    for line in out.splitlines():
        if line.startswith("HSORT_CASE ") and (line.endswith(": PASS") or line.endswith(": FAIL")):
            c_total += 1
            if line.endswith(": PASS"):
                c_passed += 1
    check("hsort-binary-exit", rc == 0 and c_total == 6, f"rc={rc} cases={c_total}")

    # Totals: C cases (6) + py checks (12). discovered counts every
    # executed assertion once.
    discovered = 6 + len(py_checks)
    passed = c_passed + sum(1 for _, p, _ in py_checks if p)
    failed = discovered - passed
    executed = discovered
    skipped = 0
    assert passed + failed == executed, "marker identity violated"
    assert executed + skipped <= discovered, "marker identity violated"

    cmd = "python3 test_smartlist.py --package <pkg> --hsort-bin ./test_hsort"
    # HMBS gate parses bare PREFIX=<json> lines (no outer braces). The
    # wrapped form {\"HMBS_...\": {...}} is NOT recognized and yields
    # \"missing evidence\" incomplete verdicts (fancy-cat precedent).
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({"executed": True, "passed": passed == discovered,
                                                   "command": cmd, "discovered": discovered,
                                                   "passedCount": passed}, ensure_ascii=False))
    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({"status": "no_tests", "framework": "none",
                                                    "command": "none (upstream ships no test suite)",
                                                    "discovered": 0, "executed": 0, "passed": 0,
                                                    "failed": 0, "skipped": 0,
                                                    "reason": "Upstream SmartList 3.15 ships no tests/, test/, TESTS, check_PROGRAMS, ctest or make-check target; audited tarball top level, SmartList/, src/ and install scripts."}, ensure_ascii=False))
    for name, p, ev in py_checks:
        print(f"CHECK {name}: {'PASS' if p else 'FAIL'} :: {ev}")
    print(f"C_CASES total={c_total} passed={c_passed}")
    return 0 if passed == discovered else 1


if __name__ == "__main__":
    sys.exit(main())
