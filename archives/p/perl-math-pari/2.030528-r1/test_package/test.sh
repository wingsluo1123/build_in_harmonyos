#!/bin/sh
# test_package/test.sh — Verify perl-math-pari package artifacts exist
# Called by test_package/conanfile.py test() method
# Arg 1: path to the package's lib/ directory
LIB_DIR="$1"
if [ -f "$LIB_DIR/Math/Pari.pm" ]; then
    echo "OK: Math::Pari.pm found at $LIB_DIR/Math/Pari.pm"
    exit 0
else
    echo "FAIL: Math::Pari.pm not found in $LIB_DIR"
    exit 1
fi
