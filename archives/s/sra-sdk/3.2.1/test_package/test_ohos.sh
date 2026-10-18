#!/bin/sh
# OHOS-specific consumer checks for sra-sdk.
set -u

BIN="$1"
LIB="$2"
fail=0

READELF=$(command -v llvm-readelf || command -v readelf)
NM=$(command -v llvm-nm || command -v nm)

# 1. Shipped tools must be AArch64 ELF binaries.
for tool in fasterq-dump vdb-dump vdb-config; do
    if ! "$READELF" -h "$BIN/$tool" 2>/dev/null | grep -q 'AArch64'; then
        echo "FAIL: $tool is not an AArch64 ELF binary"
        fail=1
    fi
done

# 2. OHOS musl does not implement pthread_cancel(); the SDK must not require it.
if "$NM" -D -u "$LIB/libncbi-vdb.so" 2>/dev/null | grep -q 'pthread_cancel'; then
    echo "FAIL: libncbi-vdb.so still references pthread_cancel (absent on OHOS musl)"
    fail=1
fi

# 3. The embedded VDB configuration must load on the device filesystem.
if ! "$BIN/vdb-config" -f > /dev/null 2>&1; then
    echo "FAIL: vdb-config could not load the embedded configuration"
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "PASS: OHOS platform checks (AArch64 tools, no pthread_cancel, kfg load)"
fi
exit "$fail"
