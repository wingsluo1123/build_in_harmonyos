#!/usr/bin/env python3
"""Consumer smoke test for the installed edid-decode binary.

Feeds three upstream sample EDIDs (test/*.test from the same snapshot) through
the *installed* executable and asserts on stable decoder output lines, then
checks the two documented non-file input paths: stdin and --help.
"""

import os
import subprocess
import sys

executable = sys.argv[1]
fixtures_dir = sys.argv[2]

# fixture file name -> substrings that must appear in the decoder output
CASES = [
    ("edid-1.0.test", ["EDID Structure Version & Revision: 1.0", "Manufacturer: MAX"]),
    ("vesa-edid-1.4-1.test", ["EDID Structure Version & Revision: 1.4", "Manufacturer: ABC"]),
    ("cta-annex-a.test", ["EDID Structure Version & Revision: 1.3", "Manufacturer: CEA"]),
]

assertions = 0
for name, expected in CASES:
    path = os.path.join(fixtures_dir, name)
    assert os.path.isfile(path), "missing fixture: %s" % path
    result = subprocess.run(
        [executable, path], check=False, capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, "%s exited %d:\n%s" % (
        name,
        result.returncode,
        output[-2000:],
    )
    assertions += 1
    for needle in expected:
        assert needle in output, "%s: %r not found in output:\n%s" % (
            name,
            needle,
            output[-2000:],
        )
        assertions += 1

# No file argument: edid-decode reads the EDID from stdin (documented behaviour).
with open(os.path.join(fixtures_dir, "edid-1.0.test"), "r") as handle:
    stdin_result = subprocess.run(
        [executable], input=handle.read(), check=False,
        capture_output=True, text=True,
    )
stdin_output = stdin_result.stdout + stdin_result.stderr
assert stdin_result.returncode == 0, "stdin decode failed:\n%s" % stdin_output[-2000:]
assertions += 1
assert "Manufacturer: MAX" in stdin_output, "stdin decode output:\n%s" % stdin_output[-2000:]
assertions += 1

# -h prints usage on stdout/stderr and exits non-zero.
usage = subprocess.run([executable, "-h"], check=False, capture_output=True, text=True)
assert usage.returncode != 0, "expected non-zero exit from -h"
assertions += 1
assert "Usage: edid-decode" in (usage.stdout + usage.stderr), "usage text missing:\n%s" % (
    usage.stdout + usage.stderr
)[-2000:]
assertions += 1

print(
    "edid-decode consumer smoke test: %d fixtures decoded, %d assertions passed"
    % (len(CASES), assertions)
)
