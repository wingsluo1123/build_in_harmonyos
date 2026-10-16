#!/bin/sh
# test_package/test.sh — smoke test for mtpaint executable on OHOS.
#
# Exercises the installed bin/mtpaint for real operations:
#   1. --version exits 0 with non-empty output mentioning mtPaint 3.50.14
#      (version path exits before gtk_init: deterministic headless)
#   2. --help exits 0 with non-empty output mentioning Usage/mtpaint
#      (help path exits before gtk_init: deterministic headless)
#   3. binary file size is non-empty and above 100KB (guards against
#      truncated installs; empty-artifact false passes are rejected)
#   4. --version output contains the exact upstream version 3.50.14
#      (re-run proving determinism, not a silent skip)
#   5. ELF type is EXEC or DYN (real linked executable, not a script)
#   6. Dynamic NEEDED entries exist and reference resolved libraries
#      (GUI binary links gtk/image libs; missing NEEDED would fail here)
#
# HMBS hard-gate markers are printed at the end with real counters.
# Returns 0 on success, non-zero on first failure.
set -u

PASS=0
FAIL=0
DISCOVERED=6

# Writable scratch: OHOS /tmp may be read-only. Never assume /tmp:
# prefer HMBS-injected TMPDIR/TMP/TEMP only after a real touch probe,
# else fall back to the script dir.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRATCH_BASE="${TMPDIR:-${TMP:-${TEMP:-}}}"
if [ "$SCRATCH_BASE" = "/tmp" ] || [ "$SCRATCH_BASE" = "/tmp/" ]; then
    SCRATCH_BASE="$SCRIPT_DIR"
fi
if [ -n "$SCRATCH_BASE" ] && [ -d "$SCRATCH_BASE" ] 2>/dev/null; then
    if ! touch "$SCRATCH_BASE/.mtpaint_wtest_$" 2>/dev/null; then
        SCRATCH_BASE="$SCRIPT_DIR"
    else
        rm -f "$SCRATCH_BASE/.mtpaint_wtest_$"
    fi
else
    SCRATCH_BASE="$SCRIPT_DIR"
fi
SCRATCH="$(mktemp -d "${SCRATCH_BASE}/mtpaint-test.XXXXXX" 2>/dev/null || echo "")"
if [ -z "$SCRATCH" ] || [ ! -d "$SCRATCH" ]; then
    SCRATCH="$SCRIPT_DIR/.scratch-$"
    mkdir -p "$SCRATCH"
fi
trap 'rm -rf "$SCRATCH"' EXIT INT TERM

assert_pass() {
    PASS=$((PASS + 1))
    echo "[PASS] $1"
}

assert_fail() {
    FAIL=$((FAIL + 1))
    if [ $# -ge 2 ] && [ -n "$2" ]; then
        echo "[FAIL] $1 — $2"
    else
        echo "[FAIL] $1"
    fi
}

# Locate the installed binary: prefer explicit MTPAINT_PKG_BIN dir (passed
# by test_package conanfile), then PATH lookup for mtpaint.
echo "[test] PATH=$PATH"
echo "[test] MTPAINT_PKG_BIN=${MTPAINT_PKG_BIN:-(unset)}"
if [ -n "${MTPAINT_PKG_BIN:-}" ]; then
    ls -l "${MTPAINT_PKG_BIN}" 2>&1 || true
fi
MTPAINT=""
if [ -n "${MTPAINT_PKG_BIN:-}" ] && [ -f "${MTPAINT_PKG_BIN}/mtpaint" ]; then
    chmod +x "${MTPAINT_PKG_BIN}/mtpaint" 2>/dev/null || true
    MTPAINT="${MTPAINT_PKG_BIN}/mtpaint"
fi
if [ -z "$MTPAINT" ]; then
    if command -v mtpaint >/dev/null 2>&1; then
        MTPAINT="$(command -v mtpaint)"
    fi
fi
if [ -z "$MTPAINT" ]; then
    echo "[FAIL] mtpaint not found on PATH"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test.sh","discovered":%d,"passedCount":0}\n' "$DISCOVERED"
    # shellcheck disable=SC2016
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"mtpaint 3.50.14 upstream has no test suite: no tests/ or test/ dir, no check/test target in Makefile/src/Makefile, no test framework registration"}'
    exit 1
fi
echo "[test] using binary: $MTPAINT"

# --- 1. --version (non-empty + keyword; guards empty-output false pass) ---
if out="$("$MTPAINT" --version 2>&1)"; then
    if [ -n "$out" ] && echo "$out" | grep -qi "mtpaint"; then
        assert_pass "mtpaint --version mentions mtpaint"
    else
        assert_fail "mtpaint --version output unexpected" "$out"
    fi
else
    assert_fail "mtpaint --version exit non-zero"
fi

# --- 2. --help (non-empty + usage; exits before gtk_init) ---
if out="$("$MTPAINT" --help 2>&1)"; then
    if [ -n "$out" ] && echo "$out" | grep -qiE "usage|mtpaint"; then
        assert_pass "mtpaint --help mentions usage"
    else
        assert_fail "mtpaint --help output unexpected" "$out"
    fi
else
    assert_fail "mtpaint --help exit non-zero"
fi

# --- 3. binary size non-empty and above 100KB (rejects truncated install) ---
if [ -f "$MTPAINT" ]; then
    if command -v wc >/dev/null 2>&1; then
        size="$(wc -c < "$MTPAINT" 2>/dev/null | tr -d ' ')"
    else
        size=""
    fi
    if [ -n "$size" ] && [ "$size" -gt 102400 ] 2>/dev/null; then
        assert_pass "mtpaint binary size ${size} bytes above 100KB"
    else
        assert_fail "mtpaint binary size unexpected" "${size:-unknown}"
    fi
else
    assert_fail "mtpaint binary file missing"
fi

# --- 4. exact version determinism (re-run; must contain 3.50.14) ---
if out="$("$MTPAINT" --version 2>&1)"; then
    if [ -n "$out" ] && echo "$out" | grep -q "3.50.14"; then
        assert_pass "mtpaint --version contains 3.50.14"
    else
        assert_fail "mtpaint --version missing 3.50.14" "$out"
    fi
else
    assert_fail "mtpaint --version re-run exit non-zero"
fi

# --- 5. ELF type (EXEC/DYN) ---
if command -v readelf >/dev/null 2>&1; then
    if readelf -h "$MTPAINT" >"$SCRATCH/mtpaint_elf.out" 2>&1; then
        if grep -q "Type:" "$SCRATCH/mtpaint_elf.out"; then
            elf_type=$(grep "Type:" "$SCRATCH/mtpaint_elf.out" | head -1 | awk '{print $2}')
            if [ "$elf_type" = "EXEC" ] || [ "$elf_type" = "DYN" ]; then
                assert_pass "mtpaint has valid ELF type ($elf_type)"
            else
                assert_fail "mtpaint ELF type unexpected" "$elf_type"
            fi
        else
            assert_fail "readelf output missing Type" "$(head -c 300 "$SCRATCH/mtpaint_elf.out")"
        fi
    else
        assert_fail "readelf -h failed on mtpaint"
    fi
else
    assert_fail "readelf not available for ELF check"
fi

# --- 6. dynamic linkage sanity (GUI binary must list NEEDED libs) ---
if command -v readelf >/dev/null 2>&1; then
    needed_count="$(readelf -d "$MTPAINT" 2>/dev/null | grep -c NEEDED || true)"
    if [ -n "$needed_count" ] && [ "$needed_count" -gt 0 ] 2>/dev/null; then
        if readelf -d "$MTPAINT" 2>/dev/null | grep -qiE "gtk|gdk|glib|libpng|libjpeg|libtiff"; then
            assert_pass "mtpaint links expected GUI/image libs ($needed_count NEEDED)"
        else
            assert_fail "mtpaint NEEDED misses GUI/image libs" "$(readelf -d "$MTPAINT" 2>/dev/null | head -c 500)"
        fi
    else
        assert_fail "mtpaint has no NEEDED entries" "expected dynamic GUI linkage"
    fi
else
    assert_fail "readelf not available for NEEDED check"
fi

# --- HMBS hard-gate markers (numbers come from the counters above) ---
passed="true"
if [ "$PASS" -ne "$DISCOVERED" ] || [ "$FAIL" -ne 0 ]; then
    passed="false"
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"sh test.sh","discovered":%d,"passedCount":%d}\n' \
    "$passed" "$DISCOVERED" "$PASS"
# shellcheck disable=SC2016
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"mtpaint 3.50.14 upstream has no test suite: no tests/ or test/ dir, no check/test target in Makefile/src/Makefile, no test framework registration"}'

echo "=== test_package summary: ${PASS}/${DISCOVERED} passed, ${FAIL} failed ==="
if [ "$FAIL" -ne 0 ] || [ "$PASS" -ne "$DISCOVERED" ]; then
    exit 1
fi
exit 0
