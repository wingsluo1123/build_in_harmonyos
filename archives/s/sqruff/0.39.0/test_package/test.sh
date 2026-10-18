#!/bin/sh
# test_package/test.sh — consumer smoke tests for the packaged sqruff binary.
# Cases: --version / --help / clean lint / dirty lint (LT01+LT12) / fix
# roundtrip / LSP initialize handshake. Runs in conanrun env (PATH includes
# installed bin/). Prints HMBS_TEST_PACKAGE_RESULT with real case counts.
#
# NOTE: `set -e` is intentionally omitted — this harness uses explicit
# PASS/FAIL counters and captures non-zero exit codes via `RC=$?` to assert
# on them; `set -e` would abort before those assertions run. `-u` and
# `pipefail` remain active (unset-variable and pipe-failure safety).
set -uo pipefail

# OHOS /tmp is read-only: prefer the harness-injected HMBS_TMPDIR, then the
# usual TMPDIR/TMP/TEMP chain (conanfile.py `_build_env` uses the same order).
WORK="${HMBS_TMPDIR:-${TMPDIR:-${TMP:-${TEMP:-/tmp}}}}/sqruff-consumer-$$"
rm -rf "$WORK"
mkdir -p "$WORK" || { echo "[fail] cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "[ok] $1"; }
bad() { FAIL=$((FAIL + 1)); echo "[fail] $1"; }

# ---- 1. sqruff --version ----
echo "[test] sqruff --version"
OUT=$(sqruff --version 2>&1); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q "0.39.0"; then
    ok "sqruff --version reports 0.39.0"
else
    bad "sqruff --version rc=$RC output: $OUT"
fi

# ---- 2. sqruff --help ----
echo "[test] sqruff --help"
OUT=$(sqruff --help 2>&1); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q "lint"; then
    ok "sqruff --help lists the lint subcommand"
else
    bad "sqruff --help rc=$RC output: $OUT"
fi

# ---- 3. clean SQL file -> no violations, rc=0 ----
echo "[test] sqruff lint clean file"
printf 'SELECT 1;\n' > "$WORK/clean.sql"
OUT=$( (cd "$WORK" && HOME="$WORK" sqruff lint -f human clean.sql) 2>&1 ); RC=$?
if [ "$RC" -eq 0 ]; then
    ok "clean file lints with rc=0"
else
    bad "clean file rc=$RC output: $OUT"
fi

# ---- 4. dirty SQL file -> LT01 + LT12, rc=1 ----
# Same fixture as upstream crates/cli/tests/lint/LT01_LT012.sql
# (SELECT + 3 spaces + no trailing newline -> layout.spacing + end_of_file).
echo "[test] sqruff lint dirty file"
printf 'SELECT   1;' > "$WORK/dirty.sql"
OUT=$( (cd "$WORK" && HOME="$WORK" sqruff lint -f human dirty.sql) 2>&1 ); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q "LT01" && \
        printf '%s' "$OUT" | grep -q "LT12"; then
    ok "dirty file reports LT01+LT12 with rc=1"
else
    bad "dirty file rc=$RC output: $OUT"
fi

# ---- 5. sqruff fix -> subsequent lint is clean ----
echo "[test] sqruff fix roundtrip"
OUT=$( (cd "$WORK" && HOME="$WORK" sqruff fix -f human dirty.sql) 2>&1 ); RC=$?
OUT2=$( (cd "$WORK" && HOME="$WORK" sqruff lint -f human dirty.sql) 2>&1 ); RC2=$?
if [ "$RC2" -eq 0 ] && [ "$(cat "$WORK/dirty.sql")" = "SELECT 1;" ]; then
    ok "fix repaired the file and re-lint is clean (fix rc=$RC)"
else
    bad "fix roundtrip fix rc=$RC relint rc=$RC2 content: $(cat "$WORK/dirty.sql") output: $OUT2"
fi

# ---- 6. sqruff lsp: LSP initialize handshake over stdio ----
# `timeout` is provided by the OHOS toybox/hnp userland on the device and the
# CI worker (millet/0.15.2 precedent, validated on the real device). If it
# (or sqruff) is missing, the case fails explicitly with rc=127 — never
# silently skipped.
echo "[test] sqruff lsp initialize handshake"
m1='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"clientInfo":{"name":"sqruff-consumer-test","version":"0.1"},"rootUri":null,"capabilities":{}}}'
m2='{"jsonrpc":"2.0","method":"initialized","params":{}}'
m3='{"jsonrpc":"2.0","id":2,"method":"shutdown"}'
m4='{"jsonrpc":"2.0","method":"exit"}'
LSP_OUT=$(
    {
        printf 'Content-Length: %s\r\n\r\n%s' "${#m1}" "$m1"
        printf 'Content-Length: %s\r\n\r\n%s' "${#m2}" "$m2"
        printf 'Content-Length: %s\r\n\r\n%s' "${#m3}" "$m3"
        printf 'Content-Length: %s\r\n\r\n%s' "${#m4}" "$m4"
    } | timeout 60 sqruff lsp 2>/dev/null
    echo "RC=$?"
)
LSP_RC=${LSP_OUT##*RC=}
if printf '%s' "$LSP_OUT" | grep -q '"capabilities"' && [ "$LSP_RC" -eq 0 ]; then
    ok "sqruff lsp answered initialize with capabilities and exited 0"
elif [ "$LSP_RC" -eq 127 ]; then
    bad "sqruff lsp handshake could not run (rc=127 — timeout or sqruff missing)"
else
    bad "sqruff lsp handshake RC=$LSP_RC output(head): $(printf '%s' "$LSP_OUT" | head -c 300)"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"/bin/sh test.sh\",\"discovered\":6,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS consumer cases passed"
