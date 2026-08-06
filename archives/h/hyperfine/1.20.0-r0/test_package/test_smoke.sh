#!/bin/sh
# test_package/test_smoke.sh — static smoke test for hyperfine precompiled binary.
#
# The packaged artifact is a precompiled aarch64 musl ELF binary from Alpine Linux.
# This test verifies packaging integrity WITHOUT executing the binary:
# on HarmonyOS the musl dynamic linker does not support LD_LIBRARY_PATH/RPATH,
# and the binary requires libgcc_s.so.1 (providing _Unwind_* symbols) which
# is not available in any system library search path (E072).
#
# Assertions:
#   1. Binary exists in the package bin/ directory
#   2. Binary is an ELF file (magic bytes check)
#   3. Binary is 64-bit aarch64 (ELF class + machine type)
#   4. Binary has execute permission
#   5. Binary has correct NEEDED entries (libgcc_s.so.1 + musl libc)
#   6. Binary size is reasonable (100KB–10MB)
#
# pipefail note: OHOS /system/bin/sh supports `set -o pipefail` (verified).
set -euo pipefail

PKG_ROOT="${1:-}"

if [ -z "$PKG_ROOT" ]; then
    echo "ERROR: package root path is required" >&2
    exit 1
fi

BINARY="$PKG_ROOT/bin/hyperfine"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# Assertion 1: binary exists
[ -f "$BINARY" ] || fail "binary not found: $BINARY"
echo "PASS: binary found at $BINARY"

# Assertion 2: ELF magic bytes
head -c 4 "$BINARY" | od -A n -t x1 | tr -d ' \n' | grep -q '^7f454c46' \
    || fail "not an ELF binary: $BINARY"
echo "PASS: ELF magic bytes verified"

# Assertion 3: 64-bit aarch64
# EI_CLASS at offset 4 (byte): 2 = ELFCLASS64
# E_MACHINE at offset 18 (2 bytes, little-endian): 183 = EM_AARCH64 (0x00b7 -> b700)
ei_class=$(od -A n -t u1 -j 4 -N 1 "$BINARY" | tr -d ' ')
[ "$ei_class" = "2" ] || fail "not 64-bit: EI_CLASS=$ei_class"
e_machine=$(od -A n -t x2 -j 18 -N 2 "$BINARY" | tr -d ' ')
[ "$e_machine" = "00b7" ] || fail "not aarch64: E_MACHINE=0x$e_machine"
echo "PASS: ELF 64-bit aarch64 verified"

# Assertion 4: executable
[ -x "$BINARY" ] || fail "binary not executable: $BINARY"
echo "PASS: binary is executable"

# Assertion 5: NEEDED entries
# Check for libgcc_s.so.1 in the dynamic section
has_libgcc=$(strings "$BINARY" | grep -c "libgcc_s.so.1" || true)
[ "$has_libgcc" -gt 0 ] || fail "missing NEEDED: libgcc_s.so.1"
has_musl=$(strings "$BINARY" | grep -c "musl" || true)
[ "$has_musl" -gt 0 ] || fail "missing NEEDED: musl libc"
echo "PASS: NEEDED entries verified (libgcc_s.so.1 + musl libc)"

# Assertion 6: reasonable size
size=$(wc -c < "$BINARY")
if [ "$size" -lt 100000 ] || [ "$size" -gt 10000000 ]; then
    fail "binary size $size outside expected range (100KB-10MB)"
fi
echo "PASS: binary size $size bytes"

echo "PASS: hyperfine smoke test: all 6 assertions passed"
