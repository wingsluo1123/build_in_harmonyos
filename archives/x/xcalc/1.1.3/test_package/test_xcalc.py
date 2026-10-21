#!/usr/bin/env python3
"""Real HarmonyOS consumer checks for the installed xcalc binary.

The checks exercise only code paths that do not need a live X server:

  * -version / --version  -> main() prints PACKAGE_STRING ("xcalc 1.1.3") and
                             exits 0 before XtAppInitialize.
  * -help    / --help     -> main() calls Syntax(1, argv), which prints the
                             usage text and exits 0 before XtAppInitialize.
  * no arguments, DISPLAY unset -> XtAppInitialize cannot open a display and
                             xcalc must report the failure and exit non-zero
                             (no hang).

Every case runs the packaged binary directly (subprocess execve, not /bin/sh)
with a hard timeout so a regression cannot hang the suite.
"""

import os
import subprocess
import sys

binary = sys.argv[1]
preload = sys.argv[2] if len(sys.argv) > 2 else ""

CASES = [
    ("-version", ["-version"], 0, "xcalc 1.1.3"),
    ("--version", ["--version"], 0, "xcalc 1.1.3"),
    ("-help", ["-help"], 0, "usage:"),
    ("--help", ["--help"], 0, "usage:"),
    ("no display", [], None, "display"),
]

passed = 0
failed = 0
for name, args, expected_rc, expected_text in CASES:
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("XAUTHORITY", None)
    if preload:
        old = env.get("LD_PRELOAD", "")
        env["LD_PRELOAD"] = ":".join(x for x in (preload, old) if x)
    try:
        result = subprocess.run(
            [binary, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            timeout=20,
        )
        output = result.stdout or ""
        rc = result.returncode
        if expected_rc is None:
            ok = rc != 0 and expected_text.lower() in output.lower()
        else:
            ok = rc == expected_rc and expected_text.lower() in output.lower()
        print(f"[test] {name}: rc={rc}")
        print(output.rstrip())
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "")
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        ok = False
        rc = None
        print(f"[test] {name}: timed out")
        print(output.rstrip())

    if ok:
        passed += 1
        print(f"[OK] {name}")
    else:
        failed += 1
        print(
            f"[FAIL] {name}; expected rc={expected_rc} and output containing "
            f"{expected_text!r}, got rc={rc}"
        )

discovered = len(CASES)
if failed:
    print(f"FAIL: {passed}/{discovered} xcalc consumer assertions passed")
    print(
        'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,'
        f'"command":"test_xcalc.py","discovered":{discovered},"passedCount":{passed}}}'
    )
    raise SystemExit(1)

print(f"OK: all {discovered} xcalc consumer assertions passed")
print(
    'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
    f'"command":"test_xcalc.py","discovered":{discovered},"passedCount":{passed}}}'
)
