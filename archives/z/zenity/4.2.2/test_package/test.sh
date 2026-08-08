#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the zenity executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

echo "[test] zenity --version"
OUTPUT=$(zenity --version) || {
    echo "FAIL: zenity --version exited with non-zero status"
    exit 1
}
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "4.2.2" || {
    echo "FAIL: expected version 4.2.2, got: $OUTPUT"
    exit 1
}
echo "OK: zenity --version returns $OUTPUT"
