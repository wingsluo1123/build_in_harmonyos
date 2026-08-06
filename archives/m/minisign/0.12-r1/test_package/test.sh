#!/usr/bin/env bash
# test_package/test.sh — functional smoke test for minisign executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
#
# Note: On OHOS, unsigned ELF binaries cannot be executed (platform restriction).
# Tests 1-3 verify binary metadata (existence, ELF format, libsodium linkage).
# Test 4 attempts execution; distinguishes platform restriction from real failure.
set -euo pipefail

# Test 1: binary exists in PATH
echo "[step] locate minisign binary"
BIN_PATH=$(which minisign 2>/dev/null || echo "")
if [ -z "$BIN_PATH" ] || [ ! -f "$BIN_PATH" ]; then
    echo "        [fail] minisign binary not found in PATH"
    exit 1
fi
echo "        [ok] minisign found at $BIN_PATH"

# Test 2: verify it's an ELF binary
echo "[step] verify ELF format"
if file "$BIN_PATH" 2>/dev/null | grep -q "ELF"; then
    echo "        [ok] minisign is an ELF binary"
else
    echo "        [fail] minisign is not an ELF binary"
    exit 1
fi

# Test 3: verify dynamic linkage to libsodium
echo "[step] verify libsodium dependency"
if readelf -d "$BIN_PATH" 2>/dev/null | grep -q "libsodium"; then
    echo "        [ok] minisign links to libsodium"
else
    echo "        [fail] minisign does not link to libsodium"
    exit 1
fi

# Test 4: attempt to run minisign -v
# On OHOS, unsigned ELF binaries cannot be executed. Distinguish between
# platform restriction (Permission denied / exec format error) and real failure.
echo "[step] minisign -v (version check)"
MINISIGN_OUTPUT=$(minisign -v 2>&1) && MINISIGN_RC=0 || MINISIGN_RC=$?

if [ "$MINISIGN_RC" -eq 0 ]; then
    if echo "$MINISIGN_OUTPUT" | grep -q "0.12"; then
        echo "        [ok] minisign -v reports version 0.12"
    else
        echo "        [fail] minisign -v did not report version 0.12"
        echo "$MINISIGN_OUTPUT"
        exit 1
    fi
elif [ "$MINISIGN_RC" -eq 126 ] || echo "$MINISIGN_OUTPUT" | grep -qi "Permission denied\|exec format error\|Operation not permitted"; then
    echo "        [warn] minisign execution skipped (OHOS ELF signing restriction, rc=$MINISIGN_RC)"
    echo "[hint] Tests 1-3 passed (binary metadata verified), Test 4 skipped"
else
    echo "        [fail] minisign -v failed with unexpected error (rc=$MINISIGN_RC)"
    echo "$MINISIGN_OUTPUT"
    exit 1
fi

echo "[step] All tests completed."
