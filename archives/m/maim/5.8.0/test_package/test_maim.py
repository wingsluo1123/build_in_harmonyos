#!/usr/bin/env python3
"""CLI-level consumer assertions for the packaged maim binary.

Invoked from test_package/conanfile.py with the conanrun environment so the
runtime X11/image shared libraries are locatable. Every assertion executes the
shipped binary and checks its real stdout/stderr and exit status; there is no
stub or shortcut.
"""

import os
import subprocess
import sys


def run(binary, *args, env=None, timeout=30):
    return subprocess.run(
        [binary, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def main():
    binary = sys.argv[1]
    checks = 0

    # 1-2. --version reports the upstream MAIM_VERSION baked in at build time.
    result = run(binary, "--version")
    assert result.returncode == 0, f"maim --version exited {result.returncode}"
    assert result.stdout.strip() == "v5.8.0", f"unexpected version: {result.stdout!r}"
    checks += 2

    # 3-8. --help renders the upstream help page and its option table.
    result = run(binary, "--help")
    assert result.returncode == 0, f"maim --help exited {result.returncode}"
    assert "maim - make image" in result.stdout, "help header missing"
    for option in ("--version", "--geometry", "--hidecursor", "--format"):
        assert option in result.stdout, f"help text lost option {option}"
        checks += 1
    checks += 2

    # 9-10. Deterministic headless failure: no reachable X display.
    env = dict(os.environ)
    env.pop("DISPLAY", None)
    env.pop("XAUTHORITY", None)
    result = run(binary, timeout=20, env=env)
    assert result.returncode == 1, f"expected clean failure without DISPLAY, got {result.returncode}"
    assert "Failed to open X display" in result.stderr, f"unexpected stderr: {result.stderr!r}"
    checks += 2

    # 11-12. An explicitly unreachable display fails the same deterministic way.
    result = run(binary, "--xdisplay=:663", timeout=20)
    assert result.returncode == 1
    assert "Failed to open X display" in result.stderr
    checks += 2

    # 13. The cxxopts option parser rejects an unknown option.
    result = run(binary, "--definitely-not-an-option")
    assert result.returncode != 0, "unknown option should be rejected"
    checks += 1

    print(f"maim CLI consumer checks passed: {checks}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
