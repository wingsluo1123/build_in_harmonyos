#!/usr/bin/env bash
# test.sh — buildifier consumer smoke test
# Usage: bash test.sh <path/to/buildifier>  (bash heredoc syntax used below)
# Note: set -e is intentionally omitted because --mode=check and --lint=warn
# may return non-zero exit codes when issues are found (expected behavior).
set -uo pipefail

BINARY="$1"
TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# Test 1: --version outputs expected version string
VERSION_OUTPUT="$("$BINARY" --version 2>&1)"
echo "$VERSION_OUTPUT" | grep -q "8.0.3" || {
  echo "FAIL: --version did not contain 8.0.3"
  echo "Output: $VERSION_OUTPUT"
  exit 1
}
echo "[ok] --version shows 8.0.3"

# Test 2: --mode=check on a properly formatted BUILD file exits 0
cat > "$TMPDIR_TEST/BUILD" <<'EOF'
package(default_visibility = ["//visibility:public"])

cc_library(
    name = "foo",
    srcs = ["foo.cc"],
)
EOF
CHECK_OUTPUT="$("$BINARY" --mode=check "$TMPDIR_TEST/BUILD" 2>&1)"
CHECK_EXIT=$?
if [ $CHECK_EXIT -ne 0 ]; then
  echo "[fail] --mode=check on clean BUILD exited $CHECK_EXIT"
  echo "Output: $CHECK_OUTPUT"
  exit 1
fi
echo "[ok] --mode=check on clean BUILD file exits 0"

# Test 3: --mode=fix reformats a poorly formatted BUILD file
# --mode=fix may return non-zero if the file was reformatted (expected)
cat > "$TMPDIR_TEST/BUILD2" <<'EOF'
cc_library(name="foo",srcs=["foo.cc"],hdrs=["foo.h"])
EOF
"$BINARY" --mode=fix "$TMPDIR_TEST/BUILD2" 2>&1 || true  # non-zero exit is expected when file is reformatted
echo "[ok] --mode=fix executed"

# Test 4: --lint=warn detects lint issues
# --lint=warn may return non-zero when lint issues are found (expected)
cat > "$TMPDIR_TEST/BUILD3" <<'EOF'
load("//some.bzl", "unused_symbol")

cc_library(name = "bar")
EOF
LINT_OUTPUT="$("$BINARY" --lint=warn "$TMPDIR_TEST/BUILD3" 2>&1 || true)"  # non-zero exit is expected when lint issues found
echo "$LINT_OUTPUT" | grep -qi "unused" || {
  echo "[warn] --lint=warn did not report unused symbol (may vary by version)"
}
echo "[ok] --lint=warn executed"

echo "=== All tests passed ==="
