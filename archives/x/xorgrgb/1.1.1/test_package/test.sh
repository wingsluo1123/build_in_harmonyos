#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for xorgrgb (showrgb) executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] showrgb --version"
showrgb --version && echo "✅ --version OK" || {
    echo "❌ showrgb --version failed"
    exit 1
}

echo "[test] showrgb color count (expect 782 lines)"
LINE_COUNT=$(showrgb | wc -l)
if [ "$LINE_COUNT" -ge 700 ]; then
    echo "✅ rgb.txt has $LINE_COUNT entries (>= 700)"
else
    echo "❌ rgb.txt only has $LINE_COUNT entries (expected ~782)"
    exit 1
fi

echo "[test] showrgb color lookup (red)"
if showrgb | grep -Eq '^[0-9]+ +[0-9]+ +[0-9]+[[:space:]]+red$'; then
    echo "✅ 'red' color found in database"
else
    echo "❌ 'red' color not found"
    exit 1
fi

echo "[test] showrgb output format check"
FIRST_LINE=$(showrgb | head -1)
if echo "$FIRST_LINE" | grep -qE '^[0-9]+ [0-9]+ [0-9]+'; then
    echo "✅ Output format valid: $FIRST_LINE"
else
    echo "❌ Invalid output format: $FIRST_LINE"
    exit 1
fi

echo "✅ All xorgrgb tests passed"
