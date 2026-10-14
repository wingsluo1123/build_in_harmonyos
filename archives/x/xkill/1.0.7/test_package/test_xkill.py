#!/usr/bin/env python3
"""Run installed xkill CLI paths without requiring an X server."""

import os
import subprocess
import sys


binary = sys.argv[1]
preload = sys.argv[2] if len(sys.argv) > 2 else ""
cases = [
    ("--version", ["--version"], 0, "xkill 1.0.7"),
    ("-version", ["-version"], 0, "xkill 1.0.7"),
    ("--help", ["--help"], 0, "usage:"),
    ("-help", ["-help"], 0, "usage:"),
    ("missing -id argument", ["-id"], 1, "-id requires an argument"),
    ("invalid zero resource id", ["-id", "0"], 1, 'invalid id "0"'),
    ("unknown option", ["--unknown"], 1, "unrecognized argument --unknown"),
    (
        "unavailable X display",
        ["-display", ":65535", "-id", "42"],
        1,
        'unable to open display ":65535"',
    ),
]

passed = 0
failed = 0
for name, args, expected_rc, expected_text in cases:
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    if preload:
        old_preload = env.get("LD_PRELOAD", "")
        env["LD_PRELOAD"] = ":".join(x for x in (preload, old_preload) if x)
    try:
        result = subprocess.run(
            [binary, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            timeout=10,
        )
        output = result.stdout or ""
        ok = result.returncode == expected_rc and expected_text.lower() in output.lower()
        print(f"[test] {name}: rc={result.returncode}")
        print(output.rstrip())
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "")
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        ok = False
        print(f"[test] {name}: timed out")
        print(output.rstrip())

    if ok:
        passed += 1
        print(f"[OK] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name}; expected rc={expected_rc} and output containing {expected_text!r}")

discovered = len(cases)
if failed:
    print(f"FAIL: {passed}/{discovered} xkill consumer assertions passed")
    print(
        'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,'
        f'"command":"test_xkill.py","discovered":{discovered},"passedCount":{passed}}}'
    )
    raise SystemExit(1)

print(f"OK: all {discovered} xkill consumer assertions passed")
print(
    'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
    f'"command":"test_xkill.py","discovered":{discovered},"passedCount":{passed}}}'
)
print(
    'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools/meson",'
    '"command":"make check","discovered":0,"executed":0,"passed":0,'
    '"failed":0,"skipped":0,"reason":"X.Org xkill 1.0.7 release contains no automated test suite"}'
)
