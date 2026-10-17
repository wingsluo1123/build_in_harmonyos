#!/bin/sh
# Consumer-side verification for xdg-utils 1.2.1 (real script execution, R34).
# Usage: test_xdg.sh <installed-bindir>
#   1. xdg-mime --version exits 0 and prints "xdg-mime 1.2.1"
#   2. xdg-mime --help exits 0
set -e
BIN_DIR="$1"
[ -x "$BIN_DIR/xdg-mime" ] || { echo "FAIL: $BIN_DIR/xdg-mime not executable"; exit 1; }

V=$("$BIN_DIR/xdg-mime" --version)
case "$V" in
    "xdg-mime 1.2.1") : ;;
    *) echo "FAIL: unexpected --version output: $V"; exit 1 ;;
esac

"$BIN_DIR/xdg-mime" --help > /dev/null
echo "xdg-utils consumer assertions passed"
