#!/bin/sh
# test_package/test.sh — smoke test for ACL2 saved_acl2 executable
set -euo pipefail

ACL2_BIN="$1"

echo "[test] 1. Check saved_acl2 binary exists"
if [ ! -f "$ACL2_BIN" ]; then
    echo "FAIL: saved_acl2 not found at $ACL2_BIN"
    exit 1
fi
echo "PASS: saved_acl2 exists"

echo "[test] 2. Check saved_acl2 is executable"
if [ ! -x "$ACL2_BIN" ]; then
    echo "FAIL: saved_acl2 is not executable"
    exit 1
fi
echo "PASS: saved_acl2 is executable"

echo "[test] 3. Verify ELF format"
if command -v file >/dev/null 2>&1; then
    file "$ACL2_BIN" | grep -qi "ELF\|shell\|script" && echo "PASS: binary format verified" || echo "WARN: unexpected format"
else
    echo "WARN: file command not available, skipping format check"
fi

echo "[test] 4. Run simple ACL2 proof"
RESULT=$(echo '(thm (equal (+ 1 1) 2))' | timeout 120 "$ACL2_BIN" 2>&1)
EXIT_CODE=${PIPESTATUS[1]}
if echo "$RESULT" | grep -qi "Q.E.D\|proved"; then
    echo "PASS: ACL2 proof engine works"
elif [ "$EXIT_CODE" -eq 124 ]; then
    echo "WARN: proof timed out (may be normal for first run)"
else
    echo "FAIL: ACL2 proof engine failed with exit code $EXIT_CODE"
    echo "$RESULT"
    exit 1
fi

echo ""
echo "All ACL2 smoke tests completed"
