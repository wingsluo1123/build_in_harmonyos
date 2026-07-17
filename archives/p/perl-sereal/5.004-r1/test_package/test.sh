#!/bin/sh
# test_package test for perl-sereal 5.004-r1
# Verifies Sereal front-end module and its XS dependencies are properly packaged.
# Note: .so runtime loading is blocked on OHOS (E046 SELinux), so file-based
# verification is used instead of runtime perl execution.
#
# Usage: bash test.sh <sereal_pm_path> <encoder_pkg_folder> <decoder_pkg_folder>

SREAL_PM="$1"
ENCODER_PKG="$2"
DECODER_PKG="$3"

PASS=0
TOTAL=0

# 1. Verify Sereal.pm exists in the front-end package
TOTAL=$((TOTAL + 1))
if [ -f "$SREAL_PM" ]; then
    PASS=$((PASS + 1))
    echo "OK: Sereal.pm found at $SREAL_PM"
else
    echo "FAIL: Sereal.pm not found at $SREAL_PM"
fi

# 2. Verify Sereal.pm contains expected module declaration and dependencies
TOTAL=$((TOTAL + 1))
if grep -q "package Sereal" "$SREAL_PM" 2>/dev/null && \
   grep -q "use Sereal::Encoder" "$SREAL_PM" 2>/dev/null && \
   grep -q "use Sereal::Decoder" "$SREAL_PM" 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "OK: Sereal.pm content valid (package declaration + Encoder/Decoder refs)"
else
    echo "FAIL: Sereal.pm content invalid"
fi

# 3. Verify Sereal::Encoder dependency is present (.pm + .so)
TOTAL=$((TOTAL + 1))
ENCODER_PM=$(find "$ENCODER_PKG" -name "Encoder.pm" 2>/dev/null | head -1)
ENCODER_SO=$(find "$ENCODER_PKG" -name "Encoder.so" 2>/dev/null | head -1)
if [ -n "$ENCODER_PM" ] && [ -n "$ENCODER_SO" ]; then
    PASS=$((PASS + 1))
    echo "OK: Sereal::Encoder package complete (.pm + .so)"
else
    echo "FAIL: Encoder.pm or Encoder.so not found in encoder package"
fi

# 4. Verify Sereal::Decoder dependency is present (.pm + .so)
TOTAL=$((TOTAL + 1))
DECODER_PM=$(find "$DECODER_PKG" -name "Decoder.pm" 2>/dev/null | head -1)
DECODER_SO=$(find "$DECODER_PKG" -name "Decoder.so" 2>/dev/null | head -1)
if [ -n "$DECODER_PM" ] && [ -n "$DECODER_SO" ]; then
    PASS=$((PASS + 1))
    echo "OK: Sereal::Decoder package complete (.pm + .so)"
else
    echo "FAIL: Decoder.pm or Decoder.so not found in decoder package"
fi

# 5. Verify Encoder.so is a valid ELF file (binary format check)
TOTAL=$((TOTAL + 1))
ENCODER_MAGIC=$(od -A n -t x1 -N 4 "$ENCODER_SO" 2>/dev/null | tr -d ' \n')
if [ "$ENCODER_MAGIC" = "7f454c46" ]; then
    PASS=$((PASS + 1))
    echo "OK: Encoder.so is valid ELF"
else
    echo "FAIL: Encoder.so is not a valid ELF file"
fi

# 6. Verify Decoder.so is a valid ELF file
TOTAL=$((TOTAL + 1))
DECODER_MAGIC=$(od -A n -t x1 -N 4 "$DECODER_SO" 2>/dev/null | tr -d ' \n')
if [ "$DECODER_MAGIC" = "7f454c46" ]; then
    PASS=$((PASS + 1))
    echo "OK: Decoder.so is valid ELF"
else
    echo "FAIL: Decoder.so is not a valid ELF file"
fi

echo "test perl-sereal 5.004-r1: $PASS/$TOTAL OK"
if [ "$PASS" -ne "$TOTAL" ]; then
    echo "FAILED: $PASS/$TOTAL tests passed"
    exit 1
fi
