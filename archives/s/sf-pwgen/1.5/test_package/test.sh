#!/bin/sh
# test_package/test.sh — HarmonyOS consumer test suite for sf-pwgen 1.5.
# Usage: test.sh [bindir]
#
# BINDIR (argv $1) is authoritative: resolved by test_package/conanfile.py
# from the sf-pwgen package_folder, so the suite fails loudly if the package
# stops shipping bin/sf-pwgen (CI L1e destructive reverse check).
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs) and
# /bin/sh materializes $(...) command substitution in hardcoded /tmp
# (ignoring TMPDIR), so this script contains ZERO $(...) / backticks.
# Output is captured with plain redirections into $TMPDIR files and asserted
# with grep/cmp/wc (counts via wc->file->grep, never via substitution).
#
# Upstream test audit: sf-pwgen 1.5 ships NO effective upstream test
# framework — the tarball has no tests/ directory, the Makefile declares
# only all/format/clean (no check or test target), and sf-pwgen-test/ holds
# an empty placeholder XCTest (testExample without assertions). All 11
# runtime cases below are NEW (9 functional + 2 HarmonyOS-specific); the
# 3 artifact ABI cases (A1-A3) live in ohos_abi_check.py. Overall 14 items.
#
# Case inventory (11 runtime check items in this file):
#   F1  default run: 5 non-empty lines
#   F2  -v prints "sf-pwgen 1.5"
#   F3  -h prints usage (upstream returns non-zero, preserved)
#   F4  letters: 3 x 12 [A-Za-z]
#   F5  alphanumeric: 2 x 16 [A-Za-z0-9]
#   F6  numbers: 2 x 10 [0-9]
#   F7  random: 2 x 12 printable non-space
#   F8  memorable: 3 lines of [a-z-]
#   F9  unknown algorithm errors
#   H1  HarmonyOS entropy: two random runs differ
#   H2  1.5 short-warning semantics: memorable -l 128 always warns
set -u

BINDIR="${1:-}"

# ---------------------------------------------------------------- TMPDIR
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export TEMPDIR="$TMPDIR"

TOTAL=11
PASS_COUNT=0
FAIL_COUNT=0

emit_markers() {
    # Upstream audit marker (authority: test_package/MANIFEST.yml).
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"sf-pwgen 1.5 ships no effective upstream test framework: no tests directory, Makefile has only all/format/clean (no check or test target), sf-pwgen-test holds an empty placeholder XCTest without assertions.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq "$TOTAL" ]; then
        echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":11,"passedCount":11}'
    else
        echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":11,"passedCount":'"$PASS_COUNT"'}'
    fi
}

ok() {
    echo "ok: $1"
    PASS_COUNT=$((PASS_COUNT+1))
}

nok() {
    echo "FAIL: $1"
    FAIL_COUNT=$((FAIL_COUNT+1))
}

abort() {
    echo "[test] ABORT: $1"
    PASS_COUNT=0
    FAIL_COUNT=$TOTAL
    emit_markers
    exit 1
}

echo "[test] sf-pwgen 1.5 HarmonyOS consumer suite (bindir='${BINDIR:-}')"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    abort "bindir not resolved"
fi
if [ ! -x "$BINDIR/sf-pwgen" ]; then
    ls -la "$BINDIR" 2>&1 || true
    abort "$BINDIR/sf-pwgen missing or not executable"
fi
echo "[test] bindir listing:"
ls -la "$BINDIR" 2>&1 || true

BIN="$BINDIR/sf-pwgen"

# ------------------------------------------------------------------- F1
# Default run: 5 non-empty lines.
echo "[test] case F1: default_run_5_passwords"
"$BIN" </dev/null >"$TMPDIR/f1.out" 2>"$TMPDIR/f1.err"
F1_RC=$?
wc -l < "$TMPDIR/f1.out" > "$TMPDIR/f1.n" 2>/dev/null || echo "0" > "$TMPDIR/f1.n"
if [ "$F1_RC" -eq 0 ] \
&& grep -qE "^ *5$" "$TMPDIR/f1.n" \
&& ! grep -q "^$" "$TMPDIR/f1.out"; then
    ok "F1 default_run_5_passwords (rc=0, 5 non-empty lines)"
else
    echo "  rc=$F1_RC (expected 0 + 5 non-empty lines)"
    cat "$TMPDIR/f1.out" "$TMPDIR/f1.err" 2>/dev/null || true
    nok "F1 default_run_5_passwords"
fi

# ------------------------------------------------------------------- F2
echo "[test] case F2: version_string"
"$BIN" -v </dev/null >"$TMPDIR/f2.out" 2>"$TMPDIR/f2.err"
F2_RC=$?
if [ "$F2_RC" -eq 0 ] \
&& grep -qE "^sf-pwgen 1\.5$" "$TMPDIR/f2.out"; then
    ok "F2 version_string (rc=0, sf-pwgen 1.5)"
else
    echo "  rc=$F2_RC"
    cat "$TMPDIR/f2.out" "$TMPDIR/f2.err" 2>/dev/null || true
    nok "F2 version_string"
fi

# ------------------------------------------------------------------- F3
# -h prints usage; upstream returns non-zero for -h (preserved here).
echo "[test] case F3: help_usage"
"$BIN" -h </dev/null >"$TMPDIR/f3.out" 2>"$TMPDIR/f3.err"
F3_RC=$?
if [ "$F3_RC" -ne 0 ] \
&& grep -q "Available options" "$TMPDIR/f3.out"; then
    ok "F3 help_usage (rc!=0 per upstream, usage on stdout)"
else
    echo "  rc=$F3_RC (expected !=0 + Available options)"
    cat "$TMPDIR/f3.out" "$TMPDIR/f3.err" 2>/dev/null || true
    nok "F3 help_usage"
fi

# ------------------------------------------------------------------- F4
echo "[test] case F4: letters_12"
"$BIN" -a letters -l 12 -c 3 </dev/null >"$TMPDIR/f4.out" 2>"$TMPDIR/f4.err"
F4_RC=$?
wc -l < "$TMPDIR/f4.out" > "$TMPDIR/f4.n" 2>/dev/null || echo "0" > "$TMPDIR/f4.n"
if [ "$F4_RC" -eq 0 ] \
&& grep -qE "^ *3$" "$TMPDIR/f4.n" \
&& ! grep -qvE "^[A-Za-z]{12}$" "$TMPDIR/f4.out"; then
    ok "F4 letters_12 (rc=0, 3 x 12 letters)"
else
    echo "  rc=$F4_RC"
    cat "$TMPDIR/f4.out" "$TMPDIR/f4.err" 2>/dev/null || true
    nok "F4 letters_12"
fi

# ------------------------------------------------------------------- F5
echo "[test] case F5: alphanumeric_16"
"$BIN" -a alphanumeric -l 16 -c 2 </dev/null >"$TMPDIR/f5.out" 2>"$TMPDIR/f5.err"
F5_RC=$?
wc -l < "$TMPDIR/f5.out" > "$TMPDIR/f5.n" 2>/dev/null || echo "0" > "$TMPDIR/f5.n"
if [ "$F5_RC" -eq 0 ] \
&& grep -qE "^ *2$" "$TMPDIR/f5.n" \
&& ! grep -qvE "^[A-Za-z0-9]{16}$" "$TMPDIR/f5.out"; then
    ok "F5 alphanumeric_16 (rc=0, 2 x 16 alnum)"
else
    echo "  rc=$F5_RC"
    cat "$TMPDIR/f5.out" "$TMPDIR/f5.err" 2>/dev/null || true
    nok "F5 alphanumeric_16"
fi

# ------------------------------------------------------------------- F6
echo "[test] case F6: numbers_10"
"$BIN" -a numbers -l 10 -c 2 </dev/null >"$TMPDIR/f6.out" 2>"$TMPDIR/f6.err"
F6_RC=$?
wc -l < "$TMPDIR/f6.out" > "$TMPDIR/f6.n" 2>/dev/null || echo "0" > "$TMPDIR/f6.n"
if [ "$F6_RC" -eq 0 ] \
&& grep -qE "^ *2$" "$TMPDIR/f6.n" \
&& ! grep -qvE "^[0-9]{10}$" "$TMPDIR/f6.out"; then
    ok "F6 numbers_10 (rc=0, 2 x 10 digits)"
else
    echo "  rc=$F6_RC"
    cat "$TMPDIR/f6.out" "$TMPDIR/f6.err" 2>/dev/null || true
    nok "F6 numbers_10"
fi

# ------------------------------------------------------------------- F7
echo "[test] case F7: random_12"
"$BIN" -a random -l 12 -c 2 </dev/null >"$TMPDIR/f7.out" 2>"$TMPDIR/f7.err"
F7_RC=$?
wc -l < "$TMPDIR/f7.out" > "$TMPDIR/f7.n" 2>/dev/null || echo "0" > "$TMPDIR/f7.n"
if [ "$F7_RC" -eq 0 ] \
&& grep -qE "^ *2$" "$TMPDIR/f7.n" \
&& ! grep -qvE "^[^ ]{12}$" "$TMPDIR/f7.out"; then
    ok "F7 random_12 (rc=0, 2 x 12 printable)"
else
    echo "  rc=$F7_RC"
    cat "$TMPDIR/f7.out" "$TMPDIR/f7.err" 2>/dev/null || true
    nok "F7 random_12"
fi

# ------------------------------------------------------------------- F8
echo "[test] case F8: memorable_words"
"$BIN" -a memorable -l 12 -c 3 </dev/null >"$TMPDIR/f8.out" 2>"$TMPDIR/f8.err"
F8_RC=$?
wc -l < "$TMPDIR/f8.out" > "$TMPDIR/f8.n" 2>/dev/null || echo "0" > "$TMPDIR/f8.n"
if [ "$F8_RC" -eq 0 ] \
&& grep -qE "^ *3$" "$TMPDIR/f8.n" \
&& ! grep -qvE "^[a-z-][a-z-]*$" "$TMPDIR/f8.out"; then
    ok "F8 memorable_words (rc=0, 3 lines of [a-z-])"
else
    echo "  rc=$F8_RC"
    cat "$TMPDIR/f8.out" "$TMPDIR/f8.err" 2>/dev/null || true
    nok "F8 memorable_words"
fi

# ------------------------------------------------------------------- F9
echo "[test] case F9: unknown_algorithm"
"$BIN" -a bogus </dev/null >"$TMPDIR/f9.out" 2>"$TMPDIR/f9.err"
F9_RC=$?
if [ "$F9_RC" -ne 0 ] \
&& grep -q "error: unknown algorithm" "$TMPDIR/f9.err"; then
    ok "F9 unknown_algorithm (rc!=0 + error message)"
else
    echo "  rc=$F9_RC (expected !=0)"
    cat "$TMPDIR/f9.out" "$TMPDIR/f9.err" 2>/dev/null || true
    nok "F9 unknown_algorithm"
fi

# ------------------------------------------------------------------- H1
# HarmonyOS entropy source: two random runs must differ.
echo "[test] case H1: harmonyos_entropy_not_repeating"
"$BIN" -a random -l 16 -c 1 </dev/null >"$TMPDIR/h1a.out" 2>"$TMPDIR/h1a.err"
H1A_RC=$?
"$BIN" -a random -l 16 -c 1 </dev/null >"$TMPDIR/h1b.out" 2>"$TMPDIR/h1b.err"
H1B_RC=$?
if [ "$H1A_RC" -eq 0 ] && [ "$H1B_RC" -eq 0 ] \
&& ! cmp -s "$TMPDIR/h1a.out" "$TMPDIR/h1b.out"; then
    ok "H1 harmonyos_entropy_not_repeating (two runs differ)"
else
    echo "  rc=$H1A_RC/$H1B_RC; identical output means the CSPRNG is not seeded"
    cat "$TMPDIR/h1a.out" "$TMPDIR/h1b.out" 2>/dev/null || true
    nok "H1 harmonyos_entropy_not_repeating"
fi

# ------------------------------------------------------------------- H2
# 1.5 short-warning semantics: 8-word cap makes -l 128 always short.
echo "[test] case H2: short_warning_semantics"
"$BIN" -a memorable -l 128 -c 1 </dev/null >"$TMPDIR/h2.out" 2>"$TMPDIR/h2.err"
H2_RC=$?
wc -l < "$TMPDIR/h2.out" > "$TMPDIR/h2.n" 2>/dev/null || echo "0" > "$TMPDIR/h2.n"
if [ "$H2_RC" -eq 0 ] \
&& grep -qE "^ *1$" "$TMPDIR/h2.n" \
&& grep -q "shorter than the requested length" "$TMPDIR/h2.err"; then
    ok "H2 short_warning_semantics (rc=0 + warning on stderr)"
else
    echo "  rc=$H2_RC (expected 0 + short warning)"
    cat "$TMPDIR/h2.out" "$TMPDIR/h2.err" 2>/dev/null || true
    nok "H2 short_warning_semantics"
fi

# ---------------------------------------------------------------- summary
emit_markers
echo "[test] summary: pass=$PASS_COUNT fail=$FAIL_COUNT (of $TOTAL)"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq "$TOTAL" ]; then
    exit 0
fi
exit 1
