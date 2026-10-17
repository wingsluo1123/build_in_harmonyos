#!/usr/bin/env python3
"""Conan test_package — skktools 1.3.4-0.20210220 consumer test.

Drives the *packaged* command-line tools (bin/skkdic-count, skkdic-sort,
skkdic-expr, skkdic-expr2) with a small ASCII SKK-JISYO fixture and asserts
their observable behaviour. All assertions are deterministic and offline.
"""
import os
import re
import subprocess
import sys

FIXTURE = [
    ";; okuri-ari entries.",
    "aa /x1/x2/",
    "ab /y1/",
    ";; okuri-nasi entries.",
    "cc /z1/z2/z3/",
    "dd /w/",
]

PART1 = [";; okuri-ari entries.", "merge /m1/", ";; okuri-nasi entries.", "only1 /o1/"]
PART2 = [";; okuri-ari entries.", "merge /m2/", ";; okuri-nasi entries.", "only2 /o2/"]

results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        results["pass"] += 1
        print("[ok] skktools: %s" % name)
    else:
        results["fail"] += 1
        print("[fail] skktools: %s %s" % (name, detail))


def run_tool(bin_dir, tool, args, stdin_data=None):
    exe = os.path.join(bin_dir, tool)
    if not os.path.isfile(exe):
        return None
    proc = subprocess.run(
        [exe] + args,
        input=stdin_data.encode("utf-8") if stdin_data is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def main():
    if len(sys.argv) < 2:
        print("[fail] skktools: package bin dir argument missing")
        sys.exit(1)
    bin_dir = sys.argv[1]
    for tool in ("skkdic-count", "skkdic-sort", "skkdic-expr", "skkdic-expr2"):
        check("binary present: %s" % tool, os.path.isfile(os.path.join(bin_dir, tool)))

    work = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
    os.makedirs(work, exist_ok=True)
    fixture = os.path.join(work, "FIXTURE.dic")
    with open(fixture, "w", newline="\n") as fh:
        fh.write("\n".join(FIXTURE) + "\n")

    # --- skkdic-count: exact candidate count (7 candidates in FIXTURE) ---
    res = run_tool(bin_dir, "skkdic-count", [fixture])
    if res:
        rc, out = res
        check("skkdic-count exit 0", rc == 0, "rc=%s out=%r" % (rc, out))
        check("skkdic-count reports 7 candidates",
              out.strip().endswith(": 7 candidates"),
              "out=%r" % out)
    else:
        check("skkdic-count executable", False)

    # --- skkdic-sort: stable, keeps keys, okuri-ari before okuri-nasi ---
    shuffled = "\n".join([
        ";; okuri-nasi entries.", "cc /z1/z2/z3/",
        ";; okuri-ari entries.", "ab /y1/", "aa /x1/x2/",
        "dd /w/",
    ]) + "\n"
    res1 = run_tool(bin_dir, "skkdic-sort", [], stdin_data=shuffled)
    res2 = run_tool(bin_dir, "skkdic-sort", [], stdin_data=shuffled)
    if res1 and res2:
        rc1, out1 = res1
        rc2, out2 = res2
        check("skkdic-sort exit 0", rc1 == 0, "rc=%s err=%r" % (rc1, out1))
        check("skkdic-sort deterministic", out1 == out2)
        check("skkdic-sort keeps all 4 keys",
              all(k in out1 for k in ("aa ", "ab ", "cc ", "dd ")))
        idx_ari = out1.find(";; okuri-ari entries.")
        idx_nasi = out1.find(";; okuri-nasi entries.")
        check("skkdic-sort okuri-ari before okuri-nasi",
              idx_ari != -1 and idx_nasi != -1 and idx_ari < idx_nasi)
    else:
        check("skkdic-sort executable", False)

    # --- skkdic-expr / skkdic-expr2: merging two dictionaries ---
    part1 = os.path.join(work, "part1.dic")
    part2 = os.path.join(work, "part2.dic")
    with open(part1, "w", newline="\n") as fh:
        fh.write("\n".join(PART1) + "\n")
    with open(part2, "w", newline="\n") as fh:
        fh.write("\n".join(PART2) + "\n")

    for tool in ("skkdic-expr", "skkdic-expr2"):
        res = run_tool(bin_dir, tool, [part1, "+", part2])
        if res:
            rc, out = res
            merged = [ln for ln in out.splitlines() if ln.startswith("merge ")]
            check("%s exit 0" % tool, rc == 0, "rc=%s err=%r" % (rc, out))
            check("%s merges both candidates" % tool,
                  len(merged) == 1 and "/m1/" in merged[0] and "/m2/" in merged[0],
                  "out=%r" % out)
            check("%s drops nothing else" % tool,
                  "only1 /o1/" in out and "only2 /o2/" in out)
        else:
            check("%s executable" % tool, False)

    print("[step] skktools test_package summary: TOTAL=%d PASS=%d FAIL=%d"
          % (results["pass"] + results["fail"], results["pass"], results["fail"]))
    sys.exit(0 if results["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
