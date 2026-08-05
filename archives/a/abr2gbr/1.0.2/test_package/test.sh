#!/bin/bash
# test_package/test.sh — smoke test for abr2gbr
set -euo pipefail

echo "[test] abr2gbr --help"
if abr2gbr --help 2>&1; then
    echo "✅ abr2gbr --help OK"
elif [ $? -ge 128 ]; then
    echo "❌ abr2gbr crashed"
    exit 1
else
    echo "✅ abr2gbr --help OK (non-zero exit expected)"
fi