#!/usr/bin/env python3
"""Consumer test source for kded5 5.116.0.

Executed by test_package/conanfile.py test() via self.run(); runs the installed
kded5 daemon with --version and asserts it prints its version.  A dedicated
test source file (not conanfile.py) is required by the L0 no_test_sources gate.
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        print("FAIL: usage: test_kded5.py <kded5-executable>")
        return 1
    exe = sys.argv[1]
    if not os.path.isfile(exe):
        print(f"FAIL: kded5 executable not found: {exe}")
        return 1
    result = subprocess.run([exe, "--version"], capture_output=True, text=True, env=os.environ)
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        print(f"FAIL: kded5 --version exited with {result.returncode}\n{output}")
        return 1
    if "kded5" not in output:
        print(f"FAIL: unexpected kded5 --version output:\n{output}")
        return 1
    version_line = next((ln for ln in output.splitlines() if "kded5" in ln), output.strip())
    print(f"PASS: kded5 --version -> {version_line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
