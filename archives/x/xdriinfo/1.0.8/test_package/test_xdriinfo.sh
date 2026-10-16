#!/bin/sh
# test_xdriinfo.sh — execute the packaged xdriinfo binary on HarmonyOS (headless).
#
# Called by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged xdriinfo binary
#   $2 = colon-joined LD_LIBRARY_PATH entries (dependency libdirs + OHOS SDK
#        runtime dirs) needed to resolve libGL.so.1 -> libgallium -> libLLVM
#        and the libxcb extension libraries
#
# POSIX sh only (HMBS [shell_getcwd]: run with the shell injected by HMBS, do
# not hardcode a bash path). No set -e/-u/pipefail: toybox ash rejects them;
# every assertion captures its own rc and always prints its output so that
# loader errors land in the log.
#
# xdriinfo.c resolves glXGetScreenDriver/glXGetDriverConfig through
# glXGetProcAddressARB before parsing argv. With mesa's libGL both pointers are
# non-NULL without an X server, so the display-independent paths below are
# reachable. "nscreens" is asserted to fail with the real XOpenDisplay error
# (DISPLAY is cleared first) — no X server exists on OHOS.

XDRIINFO_BIN="$1"
EXTRA_LIBPATH="${2:-}"

if [ -z "$XDRIINFO_BIN" ]; then
    echo "FAIL: xdriinfo binary path not provided"
    exit 1
fi

if [ ! -x "$XDRIINFO_BIN" ]; then
    echo "FAIL: $XDRIINFO_BIN not found or not executable"
    exit 1
fi

if [ -n "$EXTRA_LIBPATH" ]; then
    export LD_LIBRARY_PATH="${EXTRA_LIBPATH}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
BIN_DIR=$(dirname "$XDRIINFO_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# Make the XOpenDisplay failure path deterministic: no display requested.
unset DISPLAY

echo "[shell] $0"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] DISPLAY=${DISPLAY:-<unset>}"

discovered=5
passed=0

if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$XDRIINFO_BIN" 2>&1 || true
fi

# --- test 1: --version (xdriinfo.c strips the leading dash, then puts(PACKAGE_STRING)) ---
echo "[test 1/$discovered] xdriinfo --version"
out=$("$XDRIINFO_BIN" --version 2>&1)
rc=$?
echo "$out"
if [ $rc -ne 0 ]; then
    echo "FAIL: xdriinfo --version exit=$rc (expected 0)"
elif echo "$out" | grep -q "xdriinfo 1.0.8"; then
    echo "PASS: xdriinfo --version reports 'xdriinfo 1.0.8' (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xdriinfo --version unexpected output"
fi

# --- test 2: -version ---
echo "[test 2/$discovered] xdriinfo -version"
out=$("$XDRIINFO_BIN" -version 2>&1)
rc=$?
echo "$out"
if [ $rc -ne 0 ]; then
    echo "FAIL: xdriinfo -version exit=$rc (expected 0)"
elif echo "$out" | grep -q "xdriinfo 1.0.8"; then
    echo "PASS: xdriinfo -version reports 'xdriinfo 1.0.8' (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xdriinfo -version unexpected output"
fi

# --- test 3: -help -> printUsage() then return 0 ---
echo "[test 3/$discovered] xdriinfo -help"
out=$("$XDRIINFO_BIN" -help 2>&1)
rc=$?
echo "$out" | head -20
if [ $rc -ne 0 ]; then
    echo "FAIL: xdriinfo -help exit=$rc (expected 0)"
elif echo "$out" | grep -qi "Usage: xdriinfo"; then
    echo "PASS: xdriinfo -help prints the usage banner (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xdriinfo -help missing usage banner"
fi

# --- test 4: unrecognized option -> usage + non-zero exit ---
echo "[test 4/$discovered] xdriinfo -Zz (unrecognized option)"
out=$("$XDRIINFO_BIN" -Zz 2>&1)
rc=$?
echo "$out" | head -20
if [ $rc -eq 0 ]; then
    echo "FAIL: xdriinfo -Zz exit=0 (expected non-zero)"
elif echo "$out" | grep -qi "unrecognized argument"; then
    echo "PASS: xdriinfo -Zz rejected with a diagnostic (rc=$rc)"
    passed=$((passed + 1))
else
    echo "FAIL: xdriinfo -Zz non-zero exit but no 'unrecognized argument' message (rc=$rc)"
fi

# --- test 5: nscreens without a display -> real XOpenDisplay failure ---
echo "[test 5/$discovered] xdriinfo nscreens (no X display)"
out=$("$XDRIINFO_BIN" nscreens 2>&1)
rc=$?
echo "$out" | head -20
if [ $rc -eq 0 ]; then
    echo "FAIL: xdriinfo nscreens exit=0 (expected non-zero without a display)"
elif echo "$out" | grep -qi "Couldn't open display"; then
    echo "PASS: xdriinfo nscreens reaches XOpenDisplay and fails as expected (rc=$rc)"
    passed=$((passed + 1))
else
    echo "FAIL: xdriinfo nscreens non-zero exit but unexpected message (rc=$rc)"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xdriinfo.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xdriinfo.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
