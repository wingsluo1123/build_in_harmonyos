#!/bin/bash
# test_package/test.sh — smoke test for the zrok2 CLI executable
# Usage: bash test.sh <path-to-zrok2> [--ohos]
# Runs the actual packaged binary; every check exits nonzero on failure.
set -euo pipefail
BIN="$1"
OHOS="${2:-}"

# /tmp is read-only on OHOS (erofs); use $TMPDIR or $HOME.
TMPD="${TMPDIR:-/data/storage/el2/base/haps/entry/files}"
mkdir -p "$TMPD"
OUT="$TMPD/zrok-test-$$.out"
trap 'rm -f "$OUT"' EXIT

pass=0
fail=0

check() { # $1=desc $2=cmd...
  local desc="$1"; shift
  if "$@" > "$OUT" 2>&1; then
    pass=$((pass+1)); echo "PASS: $desc"
  else
    fail=$((fail+1)); echo "FAIL: $desc"; sed 's/^/      /' "$OUT"
  fi
}

# 1. version subcommand prints the version line
"$BIN" version > "$OUT" 2>&1 || true
if grep -q "v2.0.4" "$OUT"; then
  pass=$((pass+1)); echo "PASS: version subcommand prints v2.0.4"
else
  fail=$((fail+1)); echo "FAIL: version subcommand"; sed 's/^/      /' "$OUT"
fi

# 2. --help exits 0 and lists the CLI commands
if "$BIN" --help > "$OUT" 2>&1; then
  if grep -q "share" "$OUT" && grep -q "controller" "$OUT"; then
    pass=$((pass+1)); echo "PASS: --help lists commands"
  else
    fail=$((fail+1)); echo "FAIL: --help missing commands"; sed 's/^/      /' "$OUT"
  fi
else
  fail=$((fail+1)); echo "FAIL: --help exit code"; sed 's/^/      /' "$OUT"
fi

# 3. completion bash generates a script
"$BIN" completion bash > "$OUT" 2>&1 || true
if [ -s "$OUT" ] && head -1 "$OUT" | grep -q "bash completion"; then
  pass=$((pass+1)); echo "PASS: completion bash generates script"
else
  fail=$((fail+1)); echo "FAIL: completion bash"; head -3 "$OUT" | sed 's/^/      /'
fi

# 4. unknown subcommand returns non-zero (CLI error handling)
if "$BIN" definitely-not-a-command > "$OUT" 2>&1; then
  fail=$((fail+1)); echo "FAIL: unknown command returned 0"
else
  pass=$((pass+1)); echo "PASS: unknown command exits non-zero"
fi

if [ "$OHOS" = "--ohos" ]; then
  # strings is used to scan the ELF for section names; probe it up front so a
  # missing binary fails loudly instead of a silent false FAIL (P3).
  STRINGS=""
  if command -v strings >/dev/null 2>&1; then
    STRINGS="strings"
  elif command -v llvm-strings >/dev/null 2>&1; then
    STRINGS="llvm-strings"
  else
    echo "FAIL: strings/llvm-strings not available (needed for OHOS ELF checks)"
    fail=$((fail+1))
  fi
  if [ -n "$STRINGS" ]; then
    # Dump ELF strings to a file first, then grep the file: under `set -o
    # pipefail`, `strings BIG_BINARY | grep -q` makes grep exit on first hit
    # and strings die with SIGPIPE (141), so the pipeline reports failure even
    # though the section is present. Grepping the file avoids the race.
    STROUT="$TMPD/zrok-strings-$$.out"
    trap 'rm -f "$OUT" "$STROUT"' EXIT
    "$STRINGS" "$BIN" > "$STROUT" 2>&1 || true
    # 5. OHOS: ELF carries the binary-sign-tool signature section
    if grep -qE "\.codesign|\.note\.ohos" "$STROUT"; then
      pass=$((pass+1)); echo "PASS: OHOS signature section present"
    else
      fail=$((fail+1)); echo "FAIL: OHOS signature section missing"
    fi
    # 6. OHOS: linked against musl libc (OHOS native ABI), not glibc
    if grep -qE "ld-musl-aarch64" "$STROUT"; then
      pass=$((pass+1)); echo "PASS: musl libc linkage (OHOS native ABI)"
    else
      fail=$((fail+1)); echo "FAIL: musl linkage not found"
    fi
  fi
fi

echo "HMBS_TEST_SUMMARY: pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
