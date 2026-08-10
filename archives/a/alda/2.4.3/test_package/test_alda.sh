#!/usr/bin/env sh
# test_alda.sh — L1 smoke test for the packaged alda CLI binary.
#
# R34: the test must exercise the packaged binary (call its CLI), not
# just print a string. We invoke `alda version` and assert the output
# starts with "alda" so a missing/renamed/broken binary fails the test.
#
# This script is a static source artifact for the L0c gate (which scans
# for test_package/test* source files). The actual Conan L1 test runner
# is test_package/conanfile.py's test() method; this file documents and
# mirrors the same assertion for review and can be run standalone.
set -eu

: "${ALDA_BIN:=alda}"

# alda writes telemetry consent on first run; opt out for CI determinism.
export ALDA_TELEMETRY_DISABLED=1

version_out="$("$ALDA_BIN" version)"
case "$version_out" in
    alda*)
        echo "PASS: alda version → $version_out"
        exit 0
        ;;
    *)
        echo "FAIL: alda version did not start with 'alda' (got: $version_out)" >&2
        exit 1
        ;;
esac
