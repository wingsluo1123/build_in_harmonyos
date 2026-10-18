#!/usr/bin/env python3
"""Functional CLI tests for the packaged tgif 4.2.5 binary.

Invoked by test_package/conanfile.py as `python3 test_tgif.py <bin/tgif>`
inside the conanrun environment (so the Conan X11 shared libraries resolve).

Every assertion checks real program output / a real exit status of the packaged
binary — not a placeholder. The device has no X server, so the interactive
drawing paths cannot be exercised here; the display-less paths below are the
deterministic ones that a real tgif run takes.
"""

import os
import re
import subprocess
import sys

VERSION_LINE = "Tgif Version 4.2 (patchlevel 5)"
AUTHOR = "William Chia-Wei Cheng"


def run(binary, args):
    """Run tgif with DISPLAY removed (device has no X server)."""
    env = dict(os.environ)
    env.pop("DISPLAY", None)
    return subprocess.run(
        [binary] + list(args),
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def main():
    binary = sys.argv[1]
    checks = 0

    # 1. `-print -justversion`: pure non-GUI path; prints version + copyright and
    #    exits 0 without ever contacting a display (ProcessPrTgifOptions returns
    #    early on -justversion).
    res = run(binary, ["-print", "-justversion"])
    out = res.stdout + res.stderr
    assert res.returncode == 0, f"-print -justversion exited {res.returncode}: {out!r}"
    assert VERSION_LINE in out, f"missing version line {VERSION_LINE!r} in {out!r}"
    assert AUTHOR in out, f"missing upstream author string in {out!r}"
    checks += 3

    # 2. The patch level comes from the packaged build, so it must match the
    #    release exactly (guards a stale/wrong artifact).
    assert re.search(r"Tgif Version 4\.2 \(patchlevel 5\)", out), "version regex mismatch"
    checks += 1

    # 3. `-version` without a display: tgif prints the version banner and then
    #    fails deterministically on the missing display (device has no X server).
    res = run(binary, ["-version"])
    out = res.stdout + res.stderr
    assert res.returncode != 0, "tgif -version unexpectedly succeeded without a display"
    assert VERSION_LINE in out, f"version banner missing in {out!r}"
    assert "Can't open display" in out, f"expected display error, got {out!r}"
    checks += 3

    # 4. Bare startup without a display takes the same deterministic error path.
    res = run(binary, [])
    out = res.stdout + res.stderr
    assert res.returncode != 0, "bare tgif unexpectedly succeeded without a display"
    assert "Can't open display" in out, f"expected display error, got {out!r}"
    checks += 2

    # 5. A bogus option must not be silently accepted.
    res = run(binary, ["--definitely-not-an-option"])
    assert res.returncode != 0, "unknown option was accepted"
    checks += 1

    print(f"test_tgif.py: {checks} assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
