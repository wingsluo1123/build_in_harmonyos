#!/bin/bash
# test_package/test.sh — smoke test for abcselect
set -euo pipefail

echo "[test] abcselect --help"
abcselect --help 2>&1 || {
    echo "❌ abcselect --help failed"
    exit 1
}
echo "✅ abcselect --help OK"