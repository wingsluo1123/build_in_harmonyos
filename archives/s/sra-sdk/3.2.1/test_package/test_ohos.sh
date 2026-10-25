#!/bin/sh
# OHOS-specific consumer checks for sra-sdk.
set -eu

BIN="$1"
LIB="$2"
fail=0

READELF=$(command -v llvm-readelf || command -v readelf || true)
NM=$(command -v llvm-nm || command -v nm || true)
[ -n "$READELF" ] || { echo "FAIL: readelf/llvm-readelf not found"; exit 1; }
[ -n "$NM" ] || { echo "FAIL: nm/llvm-nm not found"; exit 1; }

# 1. Shipped tools must be AArch64 ELF binaries.
for tool in fasterq-dump vdb-dump vdb-config; do
    if [ ! -f "$BIN/$tool" ]; then
        echo "FAIL: $tool is missing"
        fail=1
        continue
    fi
    if ! hdr=$("$READELF" -h "$BIN/$tool" 2>&1); then
        echo "FAIL: $READELF failed on $tool: $hdr"
        fail=1
        continue
    fi
    case "$hdr" in
        *AArch64*) ;;
        *) echo "FAIL: $tool is not an AArch64 ELF binary"; fail=1 ;;
    esac
done

# 2. OHOS musl implements none of the POSIX thread cancellation API.
if [ ! -f "$LIB/libncbi-vdb.so" ]; then
    echo "FAIL: libncbi-vdb.so is missing from the package"
    fail=1
elif ! nm_out=$("$NM" -D -u "$LIB/libncbi-vdb.so" 2>&1); then
    echo "FAIL: $NM failed on libncbi-vdb.so: $nm_out"
    fail=1
else
    case "$nm_out" in
        *pthread_cancel*|*pthread_setcancelstate*|*pthread_setcanceltype*|*pthread_testcancel*)
            echo "FAIL: libncbi-vdb.so references pthread cancellation API (absent on OHOS musl)"
            fail=1
            ;;
    esac
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
