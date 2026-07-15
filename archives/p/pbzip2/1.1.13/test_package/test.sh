#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for pbzip2 executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] pbzip2 --version"
pbzip2 --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    pbzip2 --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ pbzip2 failed both --version and --help"
        exit 1
    }
}

echo "[test] pbzip2 compress and decompress"
TMPDIR_TEST="${TMPDIR:-/tmp}/pbzip2_test_$$"
mkdir -p "$TMPDIR_TEST"
trap "rm -rf $TMPDIR_TEST" EXIT

echo "Hello pbzip2 test data" > "$TMPDIR_TEST/test.txt"
pbzip2 -z "$TMPDIR_TEST/test.txt" && echo "✅ compress OK"
pbzip2 -d "$TMPDIR_TEST/test.txt.bz2" && echo "✅ decompress OK"
cat "$TMPDIR_TEST/test.txt" | grep -q "Hello pbzip2 test data" && echo "✅ content match OK"
