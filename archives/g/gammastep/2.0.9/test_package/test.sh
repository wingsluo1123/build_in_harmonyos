#!/bin/bash
# test_package consumer test for gammastep 2.0.9.
#
# Runs the installed `gammastep` CLI through its no-device text/query paths.
# All of them return inside argument parsing, before any adjustment backend is
# initialized — so this test never opens /dev/dri, never connects to a Wayland
# compositor and never connects to an X server (capability disclosure in
# notes.md).  The `-m list` check is a real behavioural assertion: the list is
# built from the compile-time gamma_methods[] array, so it proves that all four
# optional backends (drm/wayland/randr/vidmode) were actually compiled in.
set -u

pass=0
fail=0
ok()  { echo "PASS $1: $2"; pass=$((pass + 1)); }
bad() { echo "FAIL $1: $2"; fail=$((fail + 1)); }

echo "--- gammastep 2.0.9 consumer verification ---"

# 1. -V: exact PACKAGE_STRING on stdout, rc=0 (exits before getopt loop body)
out1=$(gammastep -V 2>/dev/null)
rc1=$?
if [ "$rc1" -eq 0 ] && [ "$out1" = "gammastep 2.0.9" ]; then
  ok 1 "-V -> rc=0 and exact 'gammastep 2.0.9'"
else
  bad 1 "-V rc=$rc1 out=[$out1]"
fi

# 2. -h: usage text on stdout, rc=0
out2=$(gammastep -h 2>/dev/null)
rc2=$?
if [ "$rc2" -eq 0 ] && echo "$out2" | grep -q "^Usage: gammastep"; then
  ok 2 "-h -> rc=0 and usage line present"
else
  bad 2 "-h rc=$rc2 out=[$out2]"
fi

# 3. -m list: rc=0 and the method list header present
out3=$(gammastep -m list 2>/dev/null)
rc3=$?
if [ "$rc3" -eq 0 ] && echo "$out3" | grep -q "Available adjustment methods:"; then
  ok 3 "-m list -> rc=0 and method-list header present"
else
  bad 3 "-m list rc=$rc3 out=[$out3]"
fi

# 4..7. -m list must name each of the four optional backends (compile-time proof)
i=4
for m in drm wayland randr vidmode; do
  if echo "$out3" | grep -qx "  $m"; then
    ok $i "-m list names backend '$m'"
  else
    bad $i "-m list missing backend '$m' (out=[$out3])"
  fi
  i=$((i + 1))
done

# 8. -m list also carries the always-built dummy backend
if echo "$out3" | grep -qx "  dummy"; then
  ok 8 "-m list names always-built backend 'dummy'"
else
  bad 8 "-m list missing 'dummy' (out=[$out3])"
fi

# 9. unknown method: stderr diagnostic + rc=1 (arg-parse error path)
err9=$(gammastep -m nosuchmethod 2>&1 >/dev/null)
rc9=$?
if [ "$rc9" -eq 1 ] && echo "$err9" | grep -q "Unknown adjustment method"; then
  ok 9 "-m nosuchmethod -> rc=1 and 'Unknown adjustment method' on stderr"
else
  bad 9 "-m nosuchmethod rc=$rc9 err=[$err9]"
fi

echo "test gammastep 2.0.9: $pass/$((pass + fail)) checks PASS"
[ "$fail" -eq 0 ] || exit 1
exit 0
