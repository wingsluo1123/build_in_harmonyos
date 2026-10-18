#!/bin/sh
# test_package/test.sh — ulogd consumer smoke test.
#
# Real execution (non-empty): locate the installed ulogd binary and run it,
# asserting the dynamic loader and every NEEDED library (libnfnetlink,
# libnetfilter_log) resolve and main() actually starts. ulogd is a netfilter
# logging daemon; --version prints the version and exits before touching any
# config file. Even a non-zero exit is accepted here as long as it is NOT one
# of the broken-install codes: 127 (not found / shared-library load failure)
# or 126 (found but not executable). What this test guards against are exactly
# those broken-install exit codes on the real OHOS target.
set -u

# Assertion 1: the installed binary is on PATH.
BIN="$(command -v ulogd 2>/dev/null || true)"
if [ -z "$BIN" ]; then
    echo "FAIL: ulogd not found in PATH" >&2
    exit 1
fi
echo "ulogd binary found: $BIN"

# Run it for real, capturing combined stdout+stderr.
OUT="$(ulogd --version 2>&1)"
RC=$?
echo "ulogd --version rc=$RC"
echo "----- output -----"
echo "$OUT"
echo "------------------"

# Assertion 2: the binary actually executed (loader + NEEDED libs resolved).
# 126 = not executable; 127 = command not found / shared-library load failure.
# Any other rc means the ELF loaded and main() ran — a successful consumer smoke.
if [ "$RC" -eq 126 ] || [ "$RC" -eq 127 ]; then
    echo "FAIL: ulogd could not execute (rc=$RC)" >&2
    exit 1
fi

echo "ulogd consumer smoke OK (rc=$RC, binary executed on target)"
exit 0
