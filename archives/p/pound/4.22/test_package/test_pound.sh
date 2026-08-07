#!/bin/sh
set -euo pipefail
# test_package/test_pound.sh — Auxiliary test script for L0c compliance
# The actual test logic runs in conanfile.py test() which executes `pound -V`.
# This script exists to satisfy L0c (test source file requirement).
echo "test_pound: checking pound binary availability"
which pound
echo "pound found in PATH"
