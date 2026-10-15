#!/bin/bash
# test_package consumer test for appres 1.0.7.
# Runs the installed `appres` binary the way a user would. All four checks
# exercise paths that return before any X connection is attempted, so they are
# meaningful on a host with no X server (DISPLAY unset).
set -u

pass=0
fail=0
ok()   { echo "PASS $1: $2"; pass=$((pass + 1)); }
bad()  { echo "FAIL $1: $2"; fail=$((fail + 1)); }

echo "--- appres 1.0.7 consumer verification ---"

# 1. -version prints the package version and exits 0
out1=$(appres -version 2>&1)
rc1=$?
if [ "$rc1" -eq 0 ] && [ "$out1" = "appres 1.0.7" ]; then
  ok 1 "-version -> [$out1]"
else
  bad 1 "-version rc=$rc1 out=[$out1]"
fi

# 2. -V is the documented short form and must agree with -version
out2=$(appres -V 2>&1)
rc2=$?
if [ "$rc2" -eq 0 ] && [ "$out2" = "appres 1.0.7" ]; then
  ok 2 "-V -> [$out2]"
else
  bad 2 "-V rc=$rc2 out=[$out2]"
fi

# 3. -help exits 0 without touching a display
appres -help > /dev/null 2>&1
rc3=$?
if [ "$rc3" -eq 0 ]; then
  ok 3 "-help exit 0"
else
  bad 3 "-help rc=$rc3"
fi

# 4. -help usage text advertises the documented options
#    (piped, not redirected to a file: no artifacts may be left behind)
help_text=$(appres -help 2>&1)
if echo "$help_text" | grep -q "usage:" && echo "$help_text" | grep -q -- "-V"; then
  ok 4 "-help usage text present"
else
  bad 4 "-help usage text missing"
fi

echo "test appres 1.0.7: $pass/$((pass + fail)) checks PASS"
[ "$fail" -eq 0 ] || exit 1
exit 0
