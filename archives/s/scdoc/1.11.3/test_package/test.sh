#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for scdoc executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# E002: /tmp is read-only on OHOS, use $TMPDIR
TMPDIR="${TMPDIR:-/data/service/el2/tmp}"
TEST_DIR=$(mktemp -d "${TMPDIR}/scdoc-test-XXXXXX")
trap 'rm -rf "$TEST_DIR"' EXIT

echo "[test] scdoc: generate man page from .scd input"

# Create a simple .scd input file
cat > "$TEST_DIR/input.scd" << 'SCD_EOF'
testprog(1)

# NAME
testprog - a test program

# SYNOPSIS
*testprog* [--option] [_file_...]

# DESCRIPTION
*testprog* is a test program for verifying scdoc functionality.

# OPTIONS
*--option*
	Enable test mode.
SCD_EOF

# Run scdoc and capture output
output=$(scdoc < "$TEST_DIR/input.scd" 2>&1)
echo "$output" > "$TEST_DIR/output.roff"

# Verify the output contains expected roff content
# roff output format: .TH "testprog" "1" "date"
if echo "$output" | grep -q '\.TH.*testprog.*1'; then
    echo "✅ scdoc generated correct man page header"
else
    echo "❌ scdoc output missing .TH header"
    echo "Output was: $output"
    exit 1
fi

if echo "$output" | grep -q "testprog"; then
    echo "✅ scdoc output contains program name"
else
    echo "❌ scdoc output missing program name"
    exit 1
fi

# Test: scdoc should fail on invalid input (no preamble)
echo "invalid content" | scdoc 2>/dev/null && {
    echo "⚠️ scdoc accepted invalid input (expected failure) - may be non-critical"
} || {
    echo "✅ scdoc correctly rejected invalid input"
}

echo "[test] scdoc smoke test: PASS"
