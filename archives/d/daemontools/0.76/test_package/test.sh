#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for daemontools binaries
# Verifies tai64n/tai64nlocal timestamp conversion and envdir functionality.
# Called by conanfile.py test() method.
set -euo pipefail

BIN_DIR="${BIN_DIR:-.}"

echo "[test] Verifying tai64n binary exists"
if [ ! -f "$BIN_DIR/tai64n" ]; then
    echo "FAIL: tai64n binary not found at $BIN_DIR/tai64n"
    exit 1
fi
echo "PASS: tai64n binary found"

echo "[test] tai64n produces TAI64N timestamp for input"
output=$(printf "hello\n" | "$BIN_DIR/tai64n")
case "$output" in
    @40000000*)
        echo "PASS: tai64n output starts with @40000000 (TAI64N format)"
        ;;
    *)
        echo "FAIL: tai64n output unexpected: $output"
        exit 1
        ;;
esac

echo "[test] tai64nlocal converts TAI64N back to local time"
local_output=$(printf "hello\n" | "$BIN_DIR/tai64n" | "$BIN_DIR/tai64nlocal")
case "$local_output" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\ *)
        echo "PASS: tai64nlocal output is a valid timestamp: $local_output"
        ;;
    *)
        echo "FAIL: tai64nlocal output unexpected: $local_output"
        exit 1
        ;;
esac

echo "[test] envdir sets environment variables from directory"
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/envdir_test.XXXXXX")
echo "world" > "$tmpdir/HELLO"
result=$("$BIN_DIR/envdir" "$tmpdir" sh -c 'echo "HELLO=$HELLO"' 2>/dev/null || true)
rm -rf "$tmpdir"
case "$result" in
    HELLO=world)
        echo "PASS: envdir correctly sets HELLO=world"
        ;;
    *)
        echo "FAIL: envdir output unexpected: $result"
        exit 1
        ;;
esac

echo "[test] svstat reports error for nonexistent service"
output=$("$BIN_DIR/svstat" /nonexistent 2>&1 || true)
case "$output" in
    *unable*|*exist*|*error*)
        echo "PASS: svstat correctly reports error for nonexistent path"
        ;;
    *)
        echo "FAIL: svstat output unexpected: $output"
        exit 1
        ;;
esac

echo "[test] All smoke tests passed"
