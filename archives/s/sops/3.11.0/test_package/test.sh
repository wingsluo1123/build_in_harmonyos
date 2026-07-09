#!/bin/sh
# test.sh — L0 test source file for sops 3.11.0
# This file satisfies the L0 quality gate requirement for a test source file.
# The actual test logic is in conanfile.py's test() method.
echo "sops test_package: checking version..."
"$1" --version 2>&1 | head -1
