#!/bin/sh
# test_package/test.sh — rolo 021 consumer test (runs in conanrun env).
# Usage: test.sh <package_folder>
# Every assertion executes the packaged binary itself (R34, no shells):
#   (A) rolo resolvable on PATH
#   (B) rolo -v prints "rolo 021" with rc 0 (exits before curses init)
#   (C) rolo -V prints the license blurb with rc 0
#   (D) rolo -h prints usage with rc 0
#   (E) headless functional run: printf 'qq' | TERM=dumb rolo -f <vCard>
#       quits cleanly with rc 0 and leaves the contacts file byte-identical
#       (mirrors the upstream run-tests headless technique).
# Upstream evidence (build-time make check parse) is staged at
# <package>/share/doc/rolo/upstream-check.json and re-emitted verbatim as
# HMBS_UPSTREAM_TEST_RESULT (single source, no recounting here).
set -u

# HMDFS: bash trusts logical PWD instead of the failing getcwd() syscall.
PWD="$(pwd)"
export PWD

PKGDIR="${1:-}"
if [ -z "$PKGDIR" ] || [ ! -d "$PKGDIR" ]; then
    echo "FAIL: package dir not resolved (argv1='${PKGDIR:-}')"
    echo "ROLO_TEST_TOTAL=0"
    echo "ROLO_TEST_PASS=0"
    echo "ROLO_TEST_FAIL=1"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh","discovered":0,"passedCount":0}'
    exit 1
fi
BINDIR="$PKGDIR/bin"
export PATH="$BINDIR:$PATH"

# Terminfo for headless curses (mirrors build() inline TERMINFO export):
# conanfile.py test() exports TERMINFO/TERMINFO_DIRS from the transitive
# ncurses package before invoking this script; just log them here for
# forensics and keep any inherited values (never override a valid export).
echo "terminfo: TERMINFO=${TERMINFO:-<unset>} TERMINFO_DIRS=${TERMINFO_DIRS:-<unset>}"
if [ -n "${TERMINFO:-}" ] && [ ! -d "$TERMINFO" ]; then
    echo "WARN: TERMINFO=$TERMINFO not a directory (headless run may fail at initscr)"
fi

# Writable scratch (HMBS injects per-task TMPDIR/TMP/TEMP; /tmp may be read-only).
# The chosen dir is exported so the rolo child (getenv TMPDIR/TMP/TEMP,
# see conanfile _fix_tmpdir_templates) honors it instead of /tmp.
_rolo_tmp_cand=""
if [ -n "${TMPDIR:-}" ] && [ -d "${TMPDIR}" ]; then
    _rolo_tmp_cand="${TMPDIR}"
elif [ -n "${TMP:-}" ] && [ -d "${TMP}" ]; then
    _rolo_tmp_cand="${TMP}"
elif [ -n "${TEMP:-}" ] && [ -d "${TEMP}" ]; then
    _rolo_tmp_cand="${TEMP}"
fi
if [ -z "$_rolo_tmp_cand" ]; then
    if [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
        _rolo_tmp_cand="$HOME/tmp"
    else
        _rolo_tmp_cand="$PWD/tmp"
    fi
fi
mkdir -p "$_rolo_tmp_cand" 2>/dev/null || true
TMPDIR="$_rolo_tmp_cand"
TMP="$_rolo_tmp_cand"
TEMP="$_rolo_tmp_cand"
export TMPDIR TMP TEMP
scratch="$TMPDIR/rolo-tp.$$"
mkdir -p "$scratch" 2>/dev/null || scratch="./tp-scratch"
mkdir -p "$scratch"
trap 'rm -rf "$scratch"' EXIT

ROLO_TEST_TOTAL=5
ROLO_TEST_PASS=0
ROLO_TEST_FAIL=0

pass() { echo "PASS: $*"; ROLO_TEST_PASS=$((ROLO_TEST_PASS + 1)); }
fail() { echo "FAIL: $*"; ROLO_TEST_FAIL=$((ROLO_TEST_FAIL + 1)); }

# ---- (A) binary present ----
if command -v rolo >/dev/null 2>&1; then
    pass "rolo resolvable on PATH ($(command -v rolo))"
else
    fail "rolo not found on PATH (bindir=$BINDIR)"
fi

# ---- (B) version banner ----
ver_out="$(rolo -v 2>&1)"
ver_rc=$?
if [ "$ver_rc" -eq 0 ] && [ "$ver_out" = "rolo 021" ]; then
    pass "rolo -v prints 'rolo 021' (rc=0)"
else
    fail "rolo -v unexpected (rc=$ver_rc, out='$ver_out')"
fi

# ---- (C) license blurb ----
lic_out="$(rolo -V 2>&1)"
lic_rc=$?
if [ "$lic_rc" -eq 0 ]; then
    if printf '%s' "$lic_out" | grep -q "GNU General Public License"; then
        pass "rolo -V prints GPL blurb (rc=0)"
    else
        fail "rolo -V missing GPL blurb: $lic_out"
    fi
else
    fail "rolo -V rc=$lic_rc"
fi

# ---- (D) usage ----
help_out="$(rolo -h 2>&1)"
help_rc=$?
if [ "$help_rc" -eq 0 ]; then
    if printf '%s' "$help_out" | grep -q "usage:"; then
        pass "rolo -h prints usage (rc=0)"
    else
        fail "rolo -h missing usage: $help_out"
    fi
else
    fail "rolo -h rc=$help_rc"
fi

# ---- (E) headless functional run (quit immediately, file untouched) ----
cat > "$scratch/contacts.vcf" <<'VCF'
BEGIN:VCARD
FN:Test Contact
N:Contact;Test;;;
TEL;TYPE=work,voice:+1-555-0100
EMAIL;TYPE=internet:test@example.com
END:VCARD
VCF
cp "$scratch/contacts.vcf" "$scratch/contacts.orig.vcf"
printf 'qq' | TERM=dumb rolo -f "$scratch/contacts.vcf" >"$scratch/run.out" 2>&1
run_rc=$?
if [ "$run_rc" -eq 0 ]; then
    if cmp -s "$scratch/contacts.vcf" "$scratch/contacts.orig.vcf"; then
        pass "headless quit rc=0, contacts file byte-identical"
    else
        fail "quit modified the contacts file (must be read-only on quit)"
    fi
else
    echo "---- headless run rc=$run_rc ----"
    cat "$scratch/run.out" 2>/dev/null || true
    fail "headless quit rc=$run_rc (want 0; TERM=dumb headless run)"
fi

echo "[test] summary: pass=$ROLO_TEST_PASS fail=$ROLO_TEST_FAIL (of $ROLO_TEST_TOTAL)"
echo "ROLO_TEST_TOTAL=$ROLO_TEST_TOTAL"
echo "ROLO_TEST_PASS=$ROLO_TEST_PASS"
echo "ROLO_TEST_FAIL=$ROLO_TEST_FAIL"

# ---- upstream evidence re-emission (byte-verbatim, single source) ----
evidence="$PKGDIR/share/doc/rolo/upstream-check.json"
if [ -f "$evidence" ]; then
    # evidence file holds exactly one compact JSON object line (written by
    # conanfile build()); re-emit it byte-verbatim as the marker payload.
    printf 'HMBS_UPSTREAM_TEST_RESULT='
    cat "$evidence"
    echo ""
else
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"error","framework":"shunit2","command":"make check","discovered":4,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"staged evidence share/doc/rolo/upstream-check.json missing from package; refusing to guess counts"}'
    fail "upstream evidence JSON missing from package"
fi

if [ "$ROLO_TEST_FAIL" -eq 0 ] && [ "$ROLO_TEST_PASS" -eq "$ROLO_TEST_TOTAL" ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":5,"passedCount":5}'
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh\",\"discovered\":$ROLO_TEST_TOTAL,\"passedCount\":$ROLO_TEST_PASS}"
    exit 1
fi
