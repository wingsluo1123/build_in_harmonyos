#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for darkice executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] darkice -h (help)"
# darkice prints version banner + usage on -h and exits
# Some versions exit with non-zero for -h, so check output instead of exit code
output=$(darkice -h 2>&1) || true
if echo "$output" | grep -q "DarkIce"; then
    echo "✅ darkice -h OK (version banner found)"
else
    echo "❌ darkice -h did not produce expected output"
    echo "$output" | head -5
    exit 1
fi

echo "[test] darkice binary exists and is executable"
which darkice && echo "✅ darkice found in PATH" || {
    echo "❌ darkice not found in PATH"
    exit 1
}

echo "[test] All smoke tests passed"
