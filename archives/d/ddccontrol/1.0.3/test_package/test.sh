#!/bin/bash
# test_package consumer test for ddccontrol 1.0.3.
# Runs the installed `ddccontrol` binary through its two no-device text paths.
# Both paths return inside argument parsing: main() prints the version banner
# before getopt(), and usage() exits before ddcci_init()/D-Bus/i2c — so this
# test never opens a device node (capability disclosure in notes.md:
# /dev/i2c-* does not exist on this host at all).
set -u

pass=0
fail=0
ok()   { echo "PASS $1: $2"; pass=$((pass + 1)); }
bad()  { echo "FAIL $1: $2"; fail=$((fail + 1)); }

echo "--- ddccontrol 1.0.3 consumer verification ---"

# 1. -h: stdout carries the version banner (printed unconditionally before getopt)
out1=$(ddccontrol -h 2>/dev/null)
if echo "$out1" | grep -q "ddccontrol version 1.0.3"; then
  ok 1 "-h stdout banner contains 'ddccontrol version 1.0.3'"
else
  bad 1 "-h stdout banner missing: [$out1]"
fi

# 2. -h: stderr carries the usage text
err2=$(ddccontrol -h 2>&1 >/dev/null)
if echo "$err2" | grep -q "^Usage:"; then
  ok 2 "-h stderr usage text present"
else
  bad 2 "-h stderr usage text missing: [$err2]"
fi

# 3. -h: exit code is 1 — upstream usage() calls exit(1), asserted as-is
ddccontrol -h >/dev/null 2>&1
rc3=$?
if [ "$rc3" -eq 1 ]; then
  ok 3 "-h exit code = 1 (upstream behavior)"
else
  bad 3 "-h exit code = $rc3 (expected 1)"
fi

# 4. bare invocation (no args): same banner + usage + rc=1, still no device access
out4=$(ddccontrol 2>/dev/null)
rc4=$?
if [ "$rc4" -eq 1 ] && echo "$out4" | grep -q "ddccontrol version 1.0.3"; then
  ok 4 "bare run -> rc=1 + version banner"
else
  bad 4 "bare run rc=$rc4 out=[$out4]"
fi

echo "test ddccontrol 1.0.3: $pass/$((pass + fail)) checks PASS"
[ "$fail" -eq 0 ] || exit 1
exit 0
