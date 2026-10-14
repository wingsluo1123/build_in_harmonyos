#!/bin/sh
# test_package consumer test for sctk 2.4.12.
# Verifies installed tools end to end:
#   1. rfilter1 (C binary) filters text using a GLM rule file
#   2. sclite (C binary) prints version info
#   3. perl-script tools are installed and executable
set -euo pipefail
cd "$(dirname "$0")"

echo "--- sctk consumer verification ---"

# 1. rfilter1 end-to-end (upstream make-check data)
rfilter1 test.arb2004.glm < test.arb2004.txt > rfilter1.out
diff -q rfilter1.out test.arb2004.txt.rfilter1 >/dev/null || {
  echo "FAIL 1: rfilter1 output mismatch"; exit 1; }
echo "PASS 1: rfilter1 (GLM filtering)"

# 2. sclite version banner (sclite -h exits non-zero, so capture output first)
sclite_out=$(sclite -h 2>&1 || true)
case "$sclite_out" in
  *"sclite Version"*) : ;;
  *) echo "FAIL 2: sclite version banner missing"; exit 1 ;;
esac
echo "PASS 2: sclite (version banner)"

# 3. perl-script tools installed (lookup via PATH, not cwd)
for t in md-eval.pl rttmSort.pl rttm2ctm.pl; do
  command -v "$t" >/dev/null 2>&1 || { echo "FAIL 3: $t missing"; exit 1; }
done
echo "PASS 3: perl-script tools present"

echo "ALL PASS"
