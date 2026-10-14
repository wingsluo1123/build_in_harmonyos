#!/bin/sh
# test_package consumer test for unscd 0.54.
# 4 checks: binary present+non-empty, `unscd -V` version output,
# `unscd --help` usage output, NSS consumer binary (test_nss.c).
# The last stdout lines are machine-readable roll-ups; test counts below
# are the single deterministic source for HMBS_TEST_PACKAGE_RESULT.
set -u

TOTAL=4
PASSED=0

# ---- resolve work dir (HMBS readonly /tmp compat) ----
WORKDIR=""
for cand in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}" "."; do
    if [ -n "${cand:-}" ] && [ "$cand" != "0" ] && [ "$cand" != "1" ]; then
        if mkdir -p "$cand" 2>/dev/null && touch "$cand/.wtest" 2>/dev/null; then
            rm -f "$cand/.wtest" 2>/dev/null || true
            WORKDIR="$cand"
            break
        fi
    fi
done
if [ -z "$WORKDIR" ]; then
    WORKDIR="."
fi

# ---- resolve unscd binary ----
UNSCD_BIN=""
if [ -n "${1:-}" ] && [ -f "${1:-}" ]; then
    UNSCD_BIN="$1"
fi
if [ -z "$UNSCD_BIN" ] && [ -n "${CONAN_UNSCD_BIN:-}" ] && [ -f "$CONAN_UNSCD_BIN" ]; then
    UNSCD_BIN="$CONAN_UNSCD_BIN"
fi
if [ -z "$UNSCD_BIN" ] && command -v unscd >/dev/null 2>&1; then
    UNSCD_BIN=$(command -v unscd)
fi
if [ -z "$UNSCD_BIN" ] && command -v nscd >/dev/null 2>&1; then
    UNSCD_BIN=$(command -v nscd)
fi
if [ -z "$UNSCD_BIN" ] || [ ! -f "$UNSCD_BIN" ]; then
    echo "FAIL: unscd binary not found (arg/CONAN_UNSCD_BIN/PATH all empty)"
    echo "=== Results: 0/$TOTAL passed ==="
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"sh test.sh\",\"discovered\":$TOTAL,\"passedCount\":0}"
    echo "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"make\",\"command\":\"make check\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"unscd-0.54 audited: single nscd-0.54.c plus 223-byte Makefile with only all/clean targets; no tests dir, no test sources, no check target\"}"
    exit 1
fi
echo "[info] using unscd binary: $UNSCD_BIN"

# ---- check 1: binary exists, non-empty, executable ----
if [ -x "$UNSCD_BIN" ] && [ ! -d "$UNSCD_BIN" ]; then
    SIZE=$(wc -c <"$UNSCD_BIN" 2>/dev/null || echo 0)
    if [ -n "$SIZE" ] && [ "$SIZE" != "0" ]; then
        echo "PASS 1: binary present, executable, size=$SIZE"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL 1: binary is empty"
    fi
else
    echo "FAIL 1: binary not executable"
fi

# ---- check 2: `unscd -V` prints version 0.54, exit 0 ----
VOUT=$("$UNSCD_BIN" -V 2>&1)
VRC=$?
if [ "$VRC" = "0" ]; then
    case "$VOUT" in
        *0.54*)
            echo "PASS 2: -V -> $VOUT"
            PASSED=$((PASSED + 1))
            ;;
        *)
            echo "FAIL 2: -V output missing 0.54 [$VOUT]"
            ;;
    esac
else
    echo "FAIL 2: -V exit=$VRC [$VOUT]"
fi

# ---- check 3: `--help` prints usage (exits 1 by upstream design) ----
HOUT=$("$UNSCD_BIN" --help 2>&1 || true)
case "$HOUT" in
    *"Usage: nscd"*)
        echo "PASS 3: --help shows usage"
        PASSED=$((PASSED + 1))
        ;;
    *)
        echo "FAIL 3: --help missing usage [$HOUT]"
        ;;
esac

# ---- check 4: NSS consumer binary (real getpwuid/getgrgid/gethostbyname) ----
NSS_SRC=""
for cand in "test_nss.c" "$(dirname "$0")/test_nss.c" "./test_nss.c"; do
    if [ -f "$cand" ]; then
        NSS_SRC="$cand"
        break
    fi
done
if [ -z "$NSS_SRC" ]; then
    echo "FAIL 4: test_nss.c not found"
else
    CCC=""
    for cand in "${CC:-}" "clang" "cc"; do
        if [ -n "${cand:-}" ] && command -v "$cand" >/dev/null 2>&1; then
            CCC="$cand"
            break
        fi
    done
    if [ -z "$CCC" ]; then
        echo "FAIL 4: no C compiler found"
    else
        NSS_BIN="$WORKDIR/test_nss_unscd"
        if "$CCC" -Wall -Os -o "$NSS_BIN" "$NSS_SRC" 2>&1; then
            NOUT=$("$NSS_BIN" 2>&1)
            NRC=$?
            echo "$NOUT"
            if [ "$NRC" = "0" ]; then
                if [ ! -s "$NSS_BIN" ]; then
                    echo "FAIL 4: NSS binary is empty (harness integrity)"
                else
                    echo "PASS 4: NSS consumer checks passed"
                    PASSED=$((PASSED + 1))
                fi
            else
                echo "FAIL 4: test_nss exit=$NRC"
            fi
            rm -f "$NSS_BIN" 2>/dev/null || true
        else
            echo "FAIL 4: test_nss.c compile failed"
        fi
    fi
fi

echo "=== Results: $PASSED/$TOTAL passed ==="

if [ "$PASSED" = "$TOTAL" ]; then
    TP_PASSED=true
else
    TP_PASSED=false
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$TP_PASSED,\"command\":\"sh test.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASSED}"
echo "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"make\",\"command\":\"make check\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"unscd-0.54 audited: single nscd-0.54.c plus 223-byte Makefile with only all/clean targets; no tests dir, no test sources, no check target\"}"

if [ "$PASSED" = "$TOTAL" ]; then
    exit 0
fi
exit 1
