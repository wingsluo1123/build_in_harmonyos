#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gawk executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# 1. Version check
gawk --version > /dev/null 2>&1 || { echo "FAIL: gawk --version"; exit 1; }

# 2. Arithmetic: 1+2*3 should equal 7
gawk 'BEGIN {exit (1+2*3==7) ? 0 : 1}' || { echo "FAIL: arithmetic"; exit 1; }

# 3. Field extraction: $1 of "hello world" should be "hello"
gawk '{exit ($1=="hello") ? 0 : 1}' <<< "hello world" || { echo "FAIL: field extraction"; exit 1; }

echo "All gawk smoke tests passed"
