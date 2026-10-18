#!/bin/sh
# test_package/test_ifmail.sh - consumer test for the packaged ifmail suite.
#
# Counting unit (the single unit used in MANIFEST.yml, notes.md and both PR
# tables): INDEPENDENT CHECK ITEMS. Every ok/bad call is one item.
#
# Everything asserted here was captured from a reference build of the same
# patched sources (macOS/arm64, native) and re-derived from the committed
# fixtures:
#   * "-h" prints "<prog> ver. 2.14-tx8.10 of <reldate>" on stderr and exits 0
#     (confusage() in iflib/rdconfig.c; the reldate part is a build timestamp,
#     so only the stable prefix is asserted);
#   * documented return codes come from the upstream man pages
#     (ifcico/ifindex.8 "RETURN CODES": 0 success, 64 usage, 65 config);
#   * the nodelist fixture encodes zone 2 / net 5020 / node 230 / point 1 with
#     sysop "John Smith", location Moscow, phone 7-095-123-4567, speed 9600
#     and flags CM,V32B (V32B implies V32 in ifcico/nlindex.c's fkey table),
#     and the config fixture maps .fidonet -> .ftn, which is what produces
#     fixtures/nlookup-v-230.expected byte for byte;
#   * make_new_ref takes no arguments and opens the compile-time REF_DBM
#     (/var/spool/ifmail/refdb), so on a system without it the documented
#     behaviour is exit(2) plus "could not open ref_db".
#
# Failure diagnostics (rc, captured output, workdir listing) are printed by the
# helpers and never influence the verdict.
#
# Usage: test_ifmail.sh [workdir]
#   workdir defaults to ./ifmail-tp-work; /tmp is never used (HMDFS /tmp is
#   read-only on OHOS).

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
WORK=${1:-$PWD/ifmail-tp-work}

PASS=0
FAIL=0

ok()  { PASS=$((PASS + 1)); printf '  [pass] %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf '  [FAIL] %s\n' "$1"; }

diag() { # <file>
    printf '    --- diagnostics: %s ---\n' "$1"
    sed -n '1,40p' "$1" 2>/dev/null | sed 's/^/    | /'
    printf '    --- diagnostics: %s listing ---\n' "$WORK"
    ls -laR "$WORK" 2>/dev/null | sed -n '1,40p' | sed 's/^/    | /'
}

# --------------------------------------------------------------- fixtures
rm -rf "$WORK"
mkdir -p "$WORK/spool/inb" "$WORK/spool/outb" "$WORK/spool/nl.d" || exit 2
cp "$SCRIPT_DIR/fixtures/nodelist.266" "$WORK/spool/nl.d/" || exit 2
sed "s|@WORKDIR@|$WORK|g" "$SCRIPT_DIR/fixtures/config.tmpl" \
    > "$WORK/config" || exit 2
CFG="$WORK/config"
DBG="$WORK/ifdebug"

# ------------------------------------------- A. packaged binaries (13 items)
# Every front end calls confusage() for -h before reading any config, so this
# works on a fresh system and proves the binary is executable and its version
# string was linked in.
for b in ifcico ifindex ifinfo ifreq ifroute nlpatch nlookup \
         ifmail ifnews iftoss ifpack ifunpack ifstat; do
    if ! command -v "$b" >/dev/null 2>&1; then
        bad "$b: not resolvable on the conanrun PATH"
        continue
    fi
    out=$("$b" -h 2>&1 </dev/null)
    rc=$?
    case "$out" in
        "$b ver. 2.14-tx8.10 of "*)
            if [ "$rc" = 0 ]; then
                ok "$b -h: rc=0 and version banner"
            else
                bad "$b -h: banner present but rc=$rc (expected 0)"
            fi
            ;;
        *)
            bad "$b -h: rc=$rc, no version banner (first line: $(printf '%s' "$out" | head -1))"
            diag "$CFG"
            ;;
    esac
done

# ---------------------------------------------- B. make_new_ref (1 item)
if command -v make_new_ref >/dev/null 2>&1; then
    out=$(make_new_ref </dev/null 2>&1)
    rc=$?
    if [ "$rc" = 2 ] && printf '%s' "$out" | grep -qF "could not open ref_db"; then
        ok "make_new_ref: documented exit(2) + reason when the compile-time ref db is absent"
    else
        bad "make_new_ref: rc=$rc (expected 2), output: $(printf '%s' "$out" | head -1)"
    fi
else
    bad "make_new_ref: not resolvable on the conanrun PATH"
fi

# --------------------------------- C. config error path: ifmail (1 item)
out=$(ifmail -I "$WORK/does-not-exist" </dev/null 2>&1)
rc=$?
if [ "$rc" = 65 ]; then
    ok "ifmail -I <missing>: rc=65 (EX_DATAERR, documented in ifmail.8)"
else
    bad "ifmail -I <missing>: rc=$rc (expected 65), output: $(printf '%s' "$out" | head -2)"
fi

# --------------------------------- D. usage error path: ifinfo (1 item)
out=$(ifinfo -I "$CFG" "not-an-address" </dev/null 2>&1)
rc=$?
if [ "$rc" = 64 ]; then
    ok "ifinfo <unparsable address>: rc=64 (EX_USAGE, documented in ifinfo.8)"
else
    bad "ifinfo <unparsable address>: rc=$rc (expected 64)"
    diag "$DBG"
fi

# ------------------------------- E. nodelist index build: ifindex (1 item)
out=$(ifindex -I "$CFG" </dev/null 2>&1)
rc=$?
if [ "$rc" = 0 ]; then
    ok "ifindex -I <fixture>: rc=0 (nodelist index built)"
else
    bad "ifindex -I <fixture>: rc=$rc (expected 0)"
    diag "$DBG"
fi

# --------------------- F. nlookup -v exact output for the node (1 item)
nlookup -I "$CFG" -v 2:5020/230 </dev/null >"$WORK/nlookup-v.out" 2>"$WORK/nlookup-v.err"
rc=$?
if [ "$rc" = 0 ] && diff -u "$SCRIPT_DIR/fixtures/nlookup-v-230.expected" \
        "$WORK/nlookup-v.out" >"$WORK/nlookup-v.diff" 2>&1; then
    ok "nlookup -v 2:5020/230: rc=0 and stdout matches the expected 8 lines byte for byte"
else
    bad "nlookup -v 2:5020/230: rc=$rc or output differs"
    diag "$WORK/nlookup-v.diff"
    diag "$WORK/nlookup-v.out"
fi

# ------------------- G. nlookup for the point under that node (1 item)
out=$(nlookup -I "$CFG" 2:5020/230.1 </dev/null 2>"$WORK/nlookup-p.err")
rc=$?
if [ "$rc" = 0 ] && [ "$out" = "Petr.Petrov@p1.f230.n5020.z2.ftn" ]; then
    ok "nlookup 2:5020/230.1: rc=0 and internet form Petr.Petrov@p1.f230.n5020.z2.ftn"
else
    bad "nlookup 2:5020/230.1: rc=$rc, got '$out'"
    diag "$DBG"
fi

# ----------------- H. nlookup for an address that is not in the index (1 item)
out=$(nlookup -I "$CFG" 2:9999/9999 </dev/null 2>"$WORK/nlookup-m.err")
rc=$?
if [ "$rc" = 0 ] && [ "$out" = "Sysop@f9999.n9999.z2.ftn" ]; then
    ok "nlookup 2:9999/9999: rc=0 and the documented dummy entry is returned"
else
    bad "nlookup 2:9999/9999: rc=$rc, got '$out'"
    diag "$DBG"
fi

# ------------------------------------------------------------------ summary
TOTAL=$((PASS + FAIL))
printf 'CONSUMER TESTS: %d/%d check items passed\n' "$PASS" "$TOTAL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
