#!/bin/sh
# test_package/test.sh — Verify perl-xml-parser package artifacts exist
# Called by test_package/conanfile.py test() method
# Arg 1: path to the package's lib/ directory
LIB_DIR="$1"
if [ -f "$LIB_DIR/XML/Parser.pm" ]; then
    echo "OK: XML::Parser.pm found at $LIB_DIR/XML/Parser.pm"
    exit 0
else
    echo "FAIL: XML::Parser.pm not found in $LIB_DIR"
    exit 1
fi
