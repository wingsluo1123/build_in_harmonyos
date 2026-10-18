#!/usr/bin/env bash
# test_tenyr.sh — genuine consumer test for the tenyr toolchain.
#
# Exercises the packaged binaries end-to-end: assemble a small tenyr program
# with `tas`, link it with `tld`, run it in the `tsim` simulator, and check
# that every shipped tool reports a version string.  Runs exactly 6 assertions
# and prints the count so the result is deterministic.
#
# Usage: test_tenyr.sh <bindir>
set -euo pipefail

BINDIR="$1"
TAS="$BINDIR/tas"
TLD="$BINDIR/tld"
TSIM="$BINDIR/tsim"

pass=0
fail=0

# A throwaway work dir.  `mkdir` (not `mktemp -d`) so we never depend on the
# HMDFS temp-dir mode quirks that break mktemp -d on OHOS; $$ is unique per run.
work="${TMPDIR:-/tmp}/tenyr-test-$$"
rm -rf "$work"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

# A minimal tenyr program: set register B to 1, then halt with `illegal`.
cat > "$work/prog.tas" <<'EOF'
B <- 1
illegal
EOF

echo "tenyr consumer test:"

# 1. The assembler accepts the program and produces a non-empty object file.
if "$TAS" -o "$work/prog.to" "$work/prog.tas" && test -s "$work/prog.to"; then
    pass=$((pass + 1)); echo "  [ok] tas assemble"
else
    fail=$((fail + 1)); echo "  [FAIL] tas assemble"
fi

# 2. The linker links the object into a non-empty executable.
if "$TLD" -o "$work/prog.texe" "$work/prog.to" && test -s "$work/prog.texe"; then
    pass=$((pass + 1)); echo "  [ok] tld link"
else
    fail=$((fail + 1)); echo "  [FAIL] tld link"
fi

# 3. The simulator loads and runs the program to completion (exit 0).
if "$TSIM" "$work/prog.texe" >/dev/null 2>&1; then
    pass=$((pass + 1)); echo "  [ok] tsim run"
else
    fail=$((fail + 1)); echo "  [FAIL] tsim run"
fi

# 4-6. Every shipped tool reports a version string and exits 0.
for tool in "$TAS" "$TLD" "$TSIM"; do
    if "$tool" -V 2>&1 | grep -qi version; then
        pass=$((pass + 1)); echo "  [ok] $tool -V"
    else
        fail=$((fail + 1)); echo "  [FAIL] $tool -V"
    fi
done

echo "tenyr test result: ${pass} passed, ${fail} failed"
test "$fail" -eq 0
