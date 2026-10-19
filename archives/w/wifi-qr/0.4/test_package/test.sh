#!/bin/sh
# wifi-qr 0.4 test_package — real-invocation tests (R34/R51).
# Invoked by conanfile.py test() with the VirtualRunEnv (conanrun) environment,
# so qrencode/zbarimg provided by dependencies are already on PATH.
set -e

fail() { echo "[FAIL] $1" >&2; exit 1; }

# 1. version banner: `wifi-qr -v` must exit 0 and print WiFi-QR 0.4
out_v="$(wifi-qr -v 2>&1)" || fail "wifi-qr -v exited $? : $out_v"
echo "$out_v" | grep -q "WiFi-QR 0.4" || fail "version banner missing, got: $out_v"

# 2. usage: `wifi-qr -h` must exit 0 and print usage header
out_h="$(wifi-qr -h 2>&1)" || fail "wifi-qr -h exited $? : $out_h"
echo "$out_h" | grep -qi "Usage" || fail "usage header missing, got: $out_h"

echo "[PASS] wifi-qr 0.4: 2/2 tests passed"
