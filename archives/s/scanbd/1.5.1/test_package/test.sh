#!/bin/sh
# test_package consumer test for scanbd.
#
# NOTE: run by bash (see test_package/conanfile.py), so -o pipefail is available.
set -u -o pipefail
#
# scanbd logs through syslog(), so stdout carries no diagnostics; the checks
# therefore assert on process behaviour (exit codes) and on packaging.
# Running the daemon proves the installed ELF loads and that its shared
# dependencies (libconfuse, libsane, libdbus) resolve at runtime.

echo "--- scanbd consumer verification ---"

command -v scanbd >/dev/null 2>&1 || { echo "FAIL: scanbd binary is not on PATH"; exit 1; }
echo "PASS 1: scanbd binary resolves -> $(command -v scanbd)"

# Foreground run pointed at an unreachable config: the daemon must start, parse
# its command line, reach the config load path and then abort with its own
# EXIT_FAILURE (1).  A 126/127 would mean the loader never ran the binary.
scanbd -f -c ./scanbd-missing-dir/scanbd.conf >/dev/null 2>&1
rc=$?
case "$rc" in
    1) echo "PASS 2: missing config -> clean EXIT_FAILURE (rc=1) after startup" ;;
    126|127) echo "FAIL: binary could not be loaded (rc=$rc)"; exit 1 ;;
    *) echo "FAIL: unexpected exit code rc=$rc"; exit 1 ;;
esac

# Unknown options must be rejected by the option parser (still a started process).
scanbd --no-such-option -f -c ./scanbd-missing-dir/scanbd.conf >/dev/null 2>&1
rc=$?
case "$rc" in
    0) echo "FAIL: unknown option was accepted (rc=0)"; exit 1 ;;
    126|127) echo "FAIL: binary could not be loaded (rc=$rc)"; exit 1 ;;
    *) echo "PASS 3: unknown option rejected (rc=$rc)" ;;
esac

# scanbd installs the scanbm compatibility entry as a symlink next to scanbd.
command -v scanbm >/dev/null 2>&1 || { echo "FAIL: scanbm compatibility entry missing"; exit 1; }
echo "PASS 4: scanbm compatibility entry resolves -> $(command -v scanbm)"

echo "test scanbd 1.5.1: 4/4 checks PASS"
exit 0
