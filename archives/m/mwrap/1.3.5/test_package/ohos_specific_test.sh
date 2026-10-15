#!/bin/bash
# ohos_specific_test.sh — ★鸿蒙新增消费者用例 (HarmonyOS consumer test).
#
# Ported from the upstream testing/ semantics onto HarmonyOS:
#   - upstream CTest log tests (mwrap.test_syntax / mwrap.test_typecheck)
#     run inside build(); here we verify the *consumer* path on the real
#     platform: end-to-end generation with a private TMPDIR (OHOS has no
#     writable /tmp), -cppcomplex support-code injection, deterministic
#     re-generation, and the missing-input error path (upstream
#     EXPECT_NONZERO semantics).
#
# Usage: ohos_specific_test.sh <bin_dir> <work_dir> <log_file>
set -u

BINDIR="$1"
WORK="$2"
LOG="$3"
MWRAP="$BINDIR/mwrap"

pass=0
fail=0

ok()  { echo "PASS: $1" | tee -a "$LOG"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1" | tee -a "$LOG"; fail=$((fail + 1)); }
note(){ echo "----" | tee -a "$LOG"; }

mkdir -p "$WORK" || exit 1
: > "$LOG"

echo "=== mwrap 1.3.5 HarmonyOS consumer test ===" | tee -a "$LOG"
echo "platform: $(uname -s) $(uname -m)" | tee -a "$LOG"

# Private TMPDIR under the caller-provided work directory — OHOS /tmp is
# read-only, so every mwrap run below must succeed with TMPDIR repointed.
PRIVATETMP="$WORK/tmp"
mkdir -p "$PRIVATETMP" || exit 1
export TMPDIR="$PRIVATETMP"

cd "$WORK" || exit 1

# ── 1. generation with private TMPDIR succeeds ──
cat > ohos_demo.mw <<'EOF'
% ohos_demo.mw — HarmonyOS consumer test input
$ void add(double a, double b, double *c) { *c = a + b; }
@function c=add(a,b)
# add(double a, double b, output double[1]c);
EOF

if "$MWRAP" -mex ohosdemomex -c ohosdemomex.cc -m ohos_demo.m ohos_demo.mw \
     >>"$LOG" 2>&1; then
  ok "mwrap generation succeeds with private TMPDIR"
else
  bad "mwrap generation failed with private TMPDIR"
fi
note

# ── 2. generated gateway is a real MEX gateway ──
if [ -s ohosdemomex.cc ] && grep -q "mexFunction" ohosdemomex.cc \
   && grep -q "#include <mex.h>" ohosdemomex.cc; then
  ok "gateway includes <mex.h> and defines mexFunction"
else
  bad "gateway contract (mex.h / mexFunction) missing"
fi
note

# ── 3. .m stub dispatches through the generated mex function ──
if [ -s ohos_demo.m ] && grep -q "ohosdemomex(mex_id_" ohos_demo.m; then
  ok ".m stub dispatches via ohosdemomex"
else
  bad ".m stub dispatch missing"
fi
note

# ── 4. -cppcomplex injects C++ complex support code ──
if "$MWRAP" -mex cpxmex -c cpxmex.cc -cppcomplex ohos_demo.mw \
     >>"$LOG" 2>&1 && grep -q "#include <complex>" cpxmex.cc; then
  ok "-cppcomplex injects C++ <complex> support code"
else
  bad "-cppcomplex support code missing"
fi
note

# ── 5. deterministic re-generation (byte-identical output) ──
if "$MWRAP" -mex ohosdemomex -c ohosdemomex.cc -m ohos_demo.m ohos_demo.mw \
     >>"$LOG" 2>&1 \
   && cp ohosdemomex.cc first_pass.cc \
   && "$MWRAP" -mex ohosdemomex -c ohosdemomex.cc -m ohos_demo.m ohos_demo.mw \
     >>"$LOG" 2>&1 \
   && cmp -s first_pass.cc ohosdemomex.cc; then
  ok "re-generation is deterministic (byte-identical gateway)"
else
  bad "re-generation differs between runs"
fi
note

# ── 6. error path: missing input file must fail (upstream EXPECT_NONZERO
#       semantics, verified on the OHOS platform) ──
if "$MWRAP" -mex nomex -c no.cc nosuch_input.mw >>"$LOG" 2>&1; then
  bad "missing input file unexpectedly succeeded"
else
  ok "missing input file fails with nonzero exit (EXPECT_NONZERO semantics)"
fi
note

echo | tee -a "$LOG"
echo "HarmonyOS consumer test: pass=$pass fail=$fail" | tee -a "$LOG"
[ "$fail" -eq 0 ]
