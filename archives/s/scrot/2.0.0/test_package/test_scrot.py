#!/usr/bin/env python3
"""test_scrot.py -- Consumer smoke test for the scrot CLI binary.

Headless-safe: exercises only metadata paths that never grab the screen
and never require an X display:
  1. scrot --version       (must exit 0 and report 2.0.0)
  2. scrot --help          (must exit 0 with non-empty help text)
  3. scrot --list-options  (must exit 0 with non-empty option list)

The caller (test_package/conanfile.py) runs this script via self.run(),
so a non-zero exit fails `conan create` and the subsequent
HMBS_TEST_PACKAGE_RESULT marker (emitted by conanfile.py) reflects
3/3 only when all three probes genuinely pass.
"""

import os
import subprocess
import sys


def find_scrot(explicit=None):
    if explicit and os.path.isfile(explicit):
        return explicit
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, "scrot")
        if os.path.isfile(candidate):
            return candidate
        candidate_exe = os.path.join(directory, "scrot.exe")
        if os.path.isfile(candidate_exe):
            return candidate_exe
    return None


def run_probe(binary, args):
    try:
        proc = subprocess.run(
            [binary] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001 - report as failure
        return -1, "", "exception: %s" % exc
    try:
        out = proc.stdout.decode("utf-8", errors="replace")
    except Exception:
        out = ""
    return proc.returncode, out, ""


def main():
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    scrot = find_scrot(explicit)
    if not scrot:
        print("FAIL: scrot binary not found (explicit=%r, PATH search failed)" % (explicit,))
        return 1
    if not os.access(scrot, os.X_OK) and os.name != "nt":
        print("FAIL: scrot binary not executable: %s" % scrot)
        return 1
    print("Found scrot binary: %s" % scrot)

    passed = 0
    failed = 0

    # 1. --version must exit 0 and mention 2.0.0 (real version gate,
    # not just "binary runs").
    rc, out, err = run_probe(scrot, ["--version"])
    if err:
        print("FAIL - scrot --version: %s" % err)
        failed += 1
    elif rc != 0:
        print("FAIL - scrot --version: exit %d, output: %r" % (rc, out[:500]))
        failed += 1
    elif "2.0.0" not in out:
        print("FAIL - scrot --version: exit 0 but '2.0.0' not in output: %r" % out[:500])
        failed += 1
    else:
        print("ok   - scrot --version reports 2.0.0")
        passed += 1

    # 2. --help must exit 0 with non-empty help text.
    rc, out, err = run_probe(scrot, ["--help"])
    if err:
        print("FAIL - scrot --help: %s" % err)
        failed += 1
    elif rc != 0:
        print("FAIL - scrot --help: exit %d, output: %r" % (rc, out[:500]))
        failed += 1
    elif not out.strip():
        print("FAIL - scrot --help: exit 0 but output empty (harness would miss it)")
        failed += 1
    else:
        print("ok   - scrot --help produced %d chars" % len(out.strip()))
        passed += 1

    # 3. --list-options must exit 0 with a non-empty machine-readable list.
    rc, out, err = run_probe(scrot, ["--list-options"])
    if err:
        print("FAIL - scrot --list-options: %s" % err)
        failed += 1
    elif rc != 0:
        print("FAIL - scrot --list-options: exit %d, output: %r" % (rc, out[:500]))
        failed += 1
    elif not out.strip():
        print("FAIL - scrot --list-options: exit 0 but output empty")
        failed += 1
    else:
        print("ok   - scrot --list-options produced %d chars" % len(out.strip()))
        passed += 1

    print("SCROT_SMOKE pass=%d fail=%d" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
