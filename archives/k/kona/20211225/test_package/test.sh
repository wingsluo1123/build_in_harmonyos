#!/usr/bin/env bash
# test_package/test.sh — smoke test for kona interpreter
# Usage: test.sh <path_to_k_binary>
set -euo pipefail

K_BIN="$1"

echo "[test] k basic arithmetic: 2+2"
result=$(echo '2+2' | "${K_BIN}" 2>&1 | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
echo "  2+2 = $result"
if [ "$result" != "4" ]; then
    echo "FAIL: expected 4, got '$result'"
    exit 1
fi

echo "[test] k multiplication: 7*8"
result=$(echo '7*8' | "${K_BIN}" 2>&1 | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
echo "  7*8 = $result"
if [ "$result" != "56" ]; then
    echo "FAIL: expected 56, got '$result'"
    exit 1
fi

echo "[test] k iota: !5"
result=$(echo '!5' | "${K_BIN}" 2>&1 | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
echo "  !5 = $result"
if [ "$result" != "0 1 2 3 4" ]; then
    echo "FAIL: expected '0 1 2 3 4', got '$result'"
    exit 1
fi

echo "[test] k sum: +/!5"
result=$(echo '+/!5' | "${K_BIN}" 2>&1 | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
echo "  +/!5 = $result"
if [ "$result" != "10" ]; then
    echo "FAIL: expected 10, got '$result'"
    exit 1
fi

echo "PASS: All kona tests passed"
