#!/usr/bin/env sh
# Smoke test for mini-httpd 1.3: run mini_httpd -V, verify exit code and version.
# Usage: test_smoke.sh <path-to-mini_httpd>
set -u

BIN="${1:-mini_httpd}"
if [ ! -x "$BIN" ]; then
    echo "FAIL: binary not executable: $BIN" >&2
    exit 1
fi

OUT="$("$BIN" -V 2>&1)"
RC=$?
if [ "$RC" -ne 0 ]; then
    echo "FAIL: $BIN -V exited $RC" >&2
    exit 1
fi

case "$OUT" in
    *"mini_httpd/1.30 26Oct2018"*)
        echo "PASS: $BIN -V -> $OUT"
        exit 0
        ;;
    *)
        echo "FAIL: unexpected version output: $OUT" >&2
        exit 1
        ;;
esac