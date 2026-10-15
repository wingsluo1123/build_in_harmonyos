#!/usr/bin/env python3
"""Detect collectors whose register-root capture will not survive AArch64.

Scans a source tree for the two patterns that decide whether a stack-scanning
(conservative) collector works on AAPCS64:

  RISK   roots are captured by spilling "dummy arguments": N live locals handed
         to a dummy function.  That construction was written for System V AMD64
         (16 argument registers); on AArch64 the caller may keep live values in
         the callee-saved registers x19-x28 instead, where a stack scan cannot
         see them, so live objects get reclaimed at -O1 and above.
  OK     the spill is forced with setjmp()/sigsetjmp(), which the ABI requires
         to preserve every callee-saved register, so the compiler has to write
         each one it uses into the frame.
  RISK   the scan's lower bound is the scanning helper's own frame address
         rather than a local of the frame that performs the scan; on AArch64 the
         16-byte red zone below sp holds caller spill slots that would be missed.

Exit codes: 0 = nothing suspicious, 1 = risk found, 2 = usage error.
usage: detect_conservative_gc.py <source-dir> [--quiet]
"""
import os
import re
import sys

SRC_EXT = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".s", ".S")

# a dummy function used only to force register spills
DUMMY_FN = re.compile(r"\b(?:static\s+)?\w[\w \*]*\b(gc_?dummy|dummy_regs?|"
                      r"spill_?regs?|force_?spill)\s*\(", re.IGNORECASE)
# many live locals handed to that dummy function
DUMMY_CALL = re.compile(r"\b\w+\s*=\s*(gc_?dummy|dummy_regs?|spill_?regs?|"
                        r"force_?spill)\s*\(([^)]*)\)", re.IGNORECASE)
SETJMP = re.compile(r"\b(sig)?setjmp\s*\(")
# stack scan driven by two addresses
SCAN = re.compile(r"for\s*\([^;]*;\s*\w+\s*!=\s*\w+\s*;\s*\w+\s*\+=\s*\w+\s*\)")
# the scan is invoked with the address of a local of the caller
SCAN_CALL = re.compile(r"\b\w*GCSI\w*\s*\([^;]*&\s*\w+\s*\)")


def scan_tree(root):
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "build", "node_modules", "__pycache__")]
        for name in filenames:
            if not name.endswith(SRC_EXT):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            findings.extend(inspect_file(path, text))
    return findings


def inspect_file(path, text):
    out = []
    lines = text.splitlines()
    dummy_defs = [i for i, l in enumerate(lines) if DUMMY_FN.search(l)]
    dummy_calls = [i for i, l in enumerate(lines) if DUMMY_CALL.search(l)]
    setjmps = [i for i, l in enumerate(lines) if SETJMP.search(l)]
    has_scan = any(SCAN.search(l) for l in lines)
    scan_calls = [i for i, l in enumerate(lines) if SCAN_CALL.search(l)]

    if dummy_calls and not setjmps:
        args = DUMMY_CALL.search(lines[dummy_calls[0]]).group(2)
        nargs = len([a for a in args.split(",") if a.strip()])
        out.append((
            "RISK", path, dummy_calls[0] + 1,
            "register roots are captured by spilling %d dummy argument(s) to a "
            "dummy function and no setjmp() is used: on AArch64 the caller may "
            "keep live values in x19-x28 across the call, where a stack scan "
            "cannot see them (fails from -O1 on, passes at -O0)" % nargs))
    elif dummy_calls and setjmps:
        out.append((
            "INFO", path, setjmps[0] + 1,
            "a dummy-argument spill is present but setjmp() is used as well; "
            "verify which one guards the collection"))
    elif setjmps and (has_scan or scan_calls):
        out.append((
            "OK", path, setjmps[0] + 1,
            "spill forced through setjmp(); the ABI makes the compiler store "
            "every callee-saved register it uses"))
    elif has_scan and dummy_defs:
        out.append((
            "INFO", path, dummy_defs[0] + 1,
            "a stack scan and a dummy function are both present; check manually "
            "whether the dummy still captures the register roots"))
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = argv[1]
    quiet = "--quiet" in argv
    if not os.path.isdir(root):
        print("not a directory: %s" % root, file=sys.stderr)
        return 2

    findings = scan_tree(root)
    risks = [f for f in findings if f[0] == "RISK"]
    for level, path, line, message in findings:
        if quiet and level != "RISK":
            continue
        print("%-5s %s:%d\n      %s" % (level, path, line, message))

    if not findings:
        print("no stack-scanning collector found under %s" % root)
        return 0
    if risks:
        print("\n%d RISK finding(s).  Validate with reproduce.sh at -O0 and -O2 "
              "before shipping: -O0 alone cannot detect this class of defect."
              % len(risks))
        return 1
    print("\nno RISK findings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
