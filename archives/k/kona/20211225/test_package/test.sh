#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for kona interpreter
# Usage: test.sh <path_to_k_binary>
set -eu

K_BIN="$1"

echo "[test] k basic arithmetic: 2+2"
result=$(echo '2+2' | "${K_BIN}" 2>&1)
echo "  2+2 = $result"
if [ -z "$result" ]; then
    echo "FAIL: k returned empty output for 2+2"
    exit 1
fi

echo "[test] k multiplication: 7*8"
result=$(echo '7*8' | "${K_BIN}" 2>&1)
echo "  7*8 = $result"
if [ -z "$result" ]; then
    echo "FAIL: k returned empty output for 7*8"
    exit 1
fi

echo "[test] k iota: !5"
result=$(echo '!5' | "${K_BIN}" 2>&1)
echo "  !5 = $result"
if [ -z "$result" ]; then
    echo "FAIL: k returned empty output for !5"
    exit 1
fi

echo "[test] k sum: +/!5"
result=$(echo '+/!5' | "${K_BIN}" 2>&1)
echo "  +/!5 = $result"
if [ -z "$result" ]; then
    echo "FAIL: k returned empty output for +/!5"
    exit 1
fi

echo "PASS: All kona tests passed"
