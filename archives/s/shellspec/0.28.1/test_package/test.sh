#!/bin/sh
# Smoke test for shellspec — verifies the installed binary works
set -e

SHELLSPEC="${SHELLSPEC_CMD:-shellspec}"

# Test: shellspec --version should output 0.28.1
version=$("$SHELLSPEC" --version 2>&1)
echo "shellspec version: $version"
if [ "$version" != "0.28.1" ]; then
    echo "FAIL: expected version 0.28.1, got '$version'"
    exit 1
fi

# Test: shellspec can run a minimal spec file
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/shellspec-test-XXXXXX")
# Create .shellspec marker (required by shellspec to recognize project dir)
touch "$tmpdir/.shellspec"

cat > "$tmpdir/smoke_spec.sh" << 'SPEC'
Describe 'smoke test'
  It 'should pass basic assertion'
    When call echo 'hello'
    The output should equal 'hello'
  End
End
SPEC

cd "$tmpdir"
"$SHELLSPEC" smoke_spec.sh --no-color 2>&1
rc=$?
rm -rf "$tmpdir"
if [ $rc -ne 0 ]; then
    echo "FAIL: shellspec spec execution failed (exit=$rc)"
    exit 1
fi

echo "shellspec smoke test: PASS"
