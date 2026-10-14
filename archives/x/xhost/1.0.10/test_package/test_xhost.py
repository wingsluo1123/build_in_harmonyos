#!/usr/bin/env python3
"""Run the packaged xhost binary and assert its headless CLI behavior."""

import os
import subprocess
import sys
from pathlib import Path


def check(label, condition, detail=""):
    if not condition:
        raise AssertionError(f"FAIL {label}: {detail}")
    print(f"[OK] {label}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_xhost.py <installed-xhost-path>")

    executable = Path(sys.argv[1])
    check("installed executable exists", executable.is_file(), str(executable))
    check("installed executable is executable", os.access(executable, os.X_OK), str(executable))

    help_result = subprocess.run(
        [str(executable), "-help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    check("-help returns the upstream status 1", help_result.returncode == 1,
          f"rc={help_result.returncode}, stderr={help_result.stderr!r}")
    check("-help prints usage", "usage:" in help_result.stderr.lower()
          and "hostname" in help_result.stderr.lower(),
          help_result.stderr[:300])

    no_display_env = os.environ.copy()
    no_display_env.pop("DISPLAY", None)
    no_display_env.pop("WAYLAND_DISPLAY", None)
    no_display_result = subprocess.run(
        [str(executable)],
        env=no_display_env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    check("no-display invocation returns 1", no_display_result.returncode == 1,
          f"rc={no_display_result.returncode}, stderr={no_display_result.stderr!r}")
    check("no-display invocation reports the X display error",
          "unable to open display" in no_display_result.stderr.lower(),
          no_display_result.stderr[:300])

    print("XHOST_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"discovered\":6,\"passedCount\":6}")


if __name__ == "__main__":
    main()