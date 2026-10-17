#!/data/service/hnp/bin/bash
# OHOS meep consumer feasibility test (rule 12)
# Structural supplement to test_consumer.cpp (which performs the real
# API call). Verifies the installed meep package is structurally
# complete and usable by consumers.
# This is NOT an assertion test — it validates real package installability.
set -eu -o pipefail

PKG="$1"
if [ -z "$PKG" ]; then
    echo "FAIL: no package dir provided"
    exit 1
fi

echo "=== Verifying meep OHOS package structure ==="

# 1. Verify include directory exists and has headers
if [ ! -d "$PKG/include" ]; then
    echo "FAIL: include directory missing: $PKG/include"
    exit 1
fi
HEADER_COUNT=$(find "$PKG/include" \( -name '*.h' -o -name '*.hpp' \) | wc -l)
if [ "$HEADER_COUNT" -eq 0 ]; then
    echo "FAIL: no headers found in $PKG/include"
    exit 1
fi
echo "OK: $HEADER_COUNT headers found"

# 2. Verify static library exists
if [ ! -f "$PKG/lib/libmeep.a" ]; then
    echo "FAIL: libmeep.a missing from $PKG/lib"
    exit 1
fi
echo "OK: libmeep.a present"

# 3. Verify library contains exported text symbols (nm)
SYMBOL_COUNT=$(nm "$PKG/lib/libmeep.a" | grep -c ' T ' || true)
SYMBOL_COUNT=${SYMBOL_COUNT:-0}
if [ "$SYMBOL_COUNT" -eq 0 ]; then
    echo "FAIL: no exported text symbols in libmeep.a"
    exit 1
fi
echo "OK: $SYMBOL_COUNT exported symbols found"

# 4. Verify pkg-config file exists (consumer-facing build integration)
if [ ! -f "$PKG/lib/pkgconfig/meep.pc" ]; then
    echo "WARN: meep.pc not found (optional for consumer build)"
else
    echo "OK: meep.pc present"
fi

echo "=== meep consumer feasibility test PASSED ==="
