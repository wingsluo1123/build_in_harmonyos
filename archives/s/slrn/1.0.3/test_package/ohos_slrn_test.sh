#!/bin/sh
# ohos_slrn_test.sh <bindir> <tmpdir>
# HarmonyOS-specific tests for slrn 1.0.3 (rule12).
# Counting unit: independent check items (3 in this script).
#
# These checks only make sense on HarmonyOS PC:
#  1. The binary reports the HarmonyOS platform from uname(2)
#     ("Operating System: OpenHarmony" / "HarmonyOS"), proving the
#     aarch64-linux-ohos triplet adaptation (config.sub patch) produced
#     an ELF that actually runs on HarmonyOS.
#  2. "S-Lang Library Version" comes from SLang_Version_String inside
#     libslang.so.2 at runtime, proving the musl dynamic linker resolves
#     the conan-provided slang shared library on OHOS (the port links
#     slang dynamically; a broken RPATH/runenv chain would fail to start
#     the binary or report a mismatched version).
#  3. A custom init file in $TMPDIR (HMDFS on HarmonyOS PC) must be read
#     and evaluated by the embedded S-Lang config engine; --show-config
#     must reflect the custom value.  This exercises the config pipeline
#     on the HarmonyOS file system (where /tmp is read-only, E002).
set -u

BINDIR="$1"
TMPDIR_TEST="$2"
SLRN="$BINDIR/slrn"
FAIL=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

export TERM="${TERM:-xterm}"
export HOME="$TMPDIR_TEST"
export TMPDIR="$TMPDIR_TEST"

echo "[info] shell uname -s: $(uname -s 2>/dev/null || echo unknown)"

"$SLRN" --version > "$TMPDIR_TEST/ohos-version.out" 2>&1
VER_RC=$?
echo "[info] slrn --version rc=$VER_RC, output:"
cat "$TMPDIR_TEST/ohos-version.out"

# Check 1: uname-reported OS must be HarmonyOS (OpenHarmony or HarmonyOS).
if [ "$VER_RC" -eq 0 ] && \
   grep -qE "Operating System: (OpenHarmony|HarmonyOS)" "$TMPDIR_TEST/ohos-version.out"; then
    pass "binary runs on HarmonyOS and reports it via uname"
else
    fail "Operating System is not OpenHarmony/HarmonyOS (rc=$VER_RC)"
fi

# Check 2: runtime S-Lang version comes from the shared library.
if [ "$VER_RC" -eq 0 ] && \
   grep -q "S-Lang Library Version: 2\.3\.3" "$TMPDIR_TEST/ohos-version.out"; then
    pass "runtime S-Lang 2.3.3 loaded from libslang.so (musl ldso)"
else
    fail "runtime S-Lang version mismatch"
fi

# Check 3: init file on HMDFS ($TMPDIR) honored by the S-Lang config engine.
RC_FILE="$TMPDIR_TEST/ohos-slrn.rc"
PROBE="slrn-ohos-hmdfs-probe-20261001"
printf 'set organization "%s"\n' "$PROBE" > "$RC_FILE"
"$SLRN" -i "$RC_FILE" --show-config > "$TMPDIR_TEST/ohos-config.out" 2>&1
CFG_RC=$?
if [ "$CFG_RC" -ne 0 ]; then
    echo "[info] slrn --show-config rc=$CFG_RC, output tail:"
    tail -20 "$TMPDIR_TEST/ohos-config.out"
fi
if [ "$CFG_RC" -eq 0 ] && \
   grep -q "organization=\"$PROBE\"" "$TMPDIR_TEST/ohos-config.out"; then
    pass "init file in \$TMPDIR (HMDFS) evaluated; --show-config reflects it"
else
    fail "init file evaluation / --show-config on HMDFS"
fi

if [ "$FAIL" -ne 0 ]; then
    echo "ohos_slrn_test.sh: FAILURES detected"
    exit 1
fi
echo "ohos_slrn_test.sh: all 3 checks passed"
exit 0
