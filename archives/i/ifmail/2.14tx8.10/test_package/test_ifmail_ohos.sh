#!/bin/sh
# test_package/test_ifmail_ohos.sh - HarmonyOS-specific tests (rule12).
#
# Counting unit (same unit as everywhere else for this package): INDEPENDENT
# CHECK ITEMS. Every ok/bad call is one item.
#
# These two tests exist because of adaptation points that are specific to this
# platform, not because they are renamed upstream tests:
#
# OHOS-1  ndbm backed by libgdbm_compat on the OHOS filesystem.
#         OHOS/musl ships no ndbm implementation at all, so every dbm_open /
#         dbm_store / dbm_fetch / dbm_firstkey call in ifmail is served by
#         gdbm's compat layer (registry package gdbm/1.23, built
#         --enable-libgdbm-compat, statically linked). That layer keeps the
#         historical two-file ndbm layout: the gdbm database lives in
#         <base>.pag and <base>.dir is an empty marker - the opposite of a BSD
#         db provider, which would put the data in <base>.db. ifindex writes
#         the index through dbm_store and nlookup reads it back through
#         dbm_fetch, so this is a real write+read round trip over the compat
#         layer on the device filesystem.
#
# OHOS-2  K&R <varargs.h> converted to C99 <stdarg.h>.
#         clang 15's <varargs.h> is an #error stub ("Please use <stdarg.h>
#         instead"), so iflib/lutil.c (loginf/logerr/debug) and
#         ifcico/respfreq.c (add_report) had to be converted; lutil.h already
#         declared them ANSI-style. A wrong conversion does not fail to build -
#         it silently mis-reads the argument list, so the check here is that
#         messages formatted through three different signatures (one %d, one
#         %s, one %s/%s/%s + %08lx, one %u x4 + %d + %lu) come out with
#         correctly substituted values in the debug file. readconfig()
#         freopen()s stderr onto debugfile, which is where these land.
#
# Expected values were captured from a reference build of the same patched
# sources and re-derived from the committed fixtures: the nodelist fixture's
# line lengths are 61/74/63/68/63 bytes, so the index offsets of the node and
# point entries are 0+61+74=135 and 135+63+68=266 (the Boss line is consumed
# by nodebld() without an index entry), and 0x139c/0x00e6 are not involved
# here - the addresses come from the nodelist text itself (2:5020/230.1).
# -x21 sets verbose to 2^21-1 = 0x001fffff, which is what the start line
# prints through %08lx.
#
# Failure diagnostics (rc, captured output, debug file, workdir listing) are
# printed by the helpers and never influence the verdict.
#
# Usage: test_ifmail_ohos.sh [workdir]
#   workdir defaults to ./ifmail-ohos-work; /tmp is never used (HMDFS /tmp is
#   read-only on OHOS).

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
WORK=${1:-$PWD/ifmail-ohos-work}

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

assert_line() { # <label> <file> <fixed-string>
    if grep -qF -- "$3" "$2" 2>/dev/null; then
        ok "$1"
    else
        bad "$1: missing '$3'"
        diag "$2"
    fi
}

# --------------------------------------------------------------- fixtures
rm -rf "$WORK"
mkdir -p "$WORK/spool/inb" "$WORK/spool/outb" "$WORK/spool/nl.d" || exit 2
cp "$SCRIPT_DIR/fixtures/nodelist.266" "$WORK/spool/nl.d/" || exit 2
sed "s|@WORKDIR@|$WORK|g" "$SCRIPT_DIR/fixtures/config.tmpl" \
    > "$WORK/config" || exit 2
CFG="$WORK/config"
DBG="$WORK/ifdebug"
NLD="$WORK/spool/nl.d"

for b in ifindex nlookup; do
    if ! command -v "$b" >/dev/null 2>&1; then
        printf 'FATAL: %s is not on the conanrun PATH - the package under test is missing\n' "$b"
        exit 2
    fi
done

# ============================ OHOS-1: ndbm over libgdbm_compat (5 items) ====
printf 'OHOS-1 ndbm/libgdbm_compat round trip in %s\n' "$NLD"

# -x21 so the run also leaves its trace in the debug file (readconfig()
# freopen()s stderr onto debugfile, and with verbose=0 nothing is written);
# OHOS-1e asserts on that trace.
ifindex -x21 -I "$CFG" </dev/null >"$WORK/ix1.out" 2>"$WORK/ix1.err"
rc=$?
if [ "$rc" = 0 ]; then
    ok "OHOS-1a ifindex -x21 on a fresh directory: rc=0 (dbm_open + dbm_store through libgdbm_compat)"
else
    bad "OHOS-1a ifindex on a fresh directory: rc=$rc (expected 0)"
    diag "$WORK/ix1.err"
fi

# gdbm's ndbm compat keeps the database in <base>.pag and leaves <base>.dir as
# an empty marker; a non-empty .pag proves dbm_store really wrote through the
# compat layer rather than silently doing nothing. This item is the one place
# where a macOS reference build legitimately differs: BSD db puts the data in
# index.db, so OHOS-1b can only pass on the device (noted as locally
# unverifiable, not asserted any other way).
if [ -s "$NLD/index.pag" ]; then
    ok "OHOS-1b ndbm data file index.pag is non-empty ($(wc -c <"$NLD/index.pag" | tr -d ' ') bytes, gdbm compat layout)"
else
    bad "OHOS-1b ndbm data file $NLD/index.pag is missing or empty"
    diag "$NLD"
fi

nlookup -I "$CFG" -v 2:5020/230 </dev/null >"$WORK/nl1.out" 2>"$WORK/nl1.err"
rc=$?
if [ "$rc" = 0 ] && diff -u "$SCRIPT_DIR/fixtures/nlookup-v-230.expected" \
        "$WORK/nl1.out" >"$WORK/nl1.diff" 2>&1; then
    ok "OHOS-1c nlookup reads the index back through dbm_fetch: stdout matches the expected 8 lines byte for byte"
else
    bad "OHOS-1c nlookup read-back: rc=$rc or output differs"
    diag "$WORK/nl1.diff"
    diag "$WORK/nl1.out"
fi

# Re-opening an existing gdbm-backed ndbm database is a different code path
# from creating one (initnl() checks the index mtime, nodebld() truncates and
# re-stores), so run the rebuild a second time.
ifindex -x21 -I "$CFG" </dev/null >"$WORK/ix2.out" 2>"$WORK/ix2.err"
rc=$?
if [ "$rc" = 0 ]; then
    ok "OHOS-1d ifindex rebuild over the existing index: rc=0 (dbm_open on an existing gdbm file)"
else
    bad "OHOS-1d ifindex rebuild: rc=$rc (expected 0)"
    diag "$WORK/ix2.err"
fi

assert_line "OHOS-1e index holds all four fixture entries" "$DBG" \
    "Total 4 entries in nodelist index"

# ============== OHOS-2: K&R varargs -> C99 stdarg on clang 15 (7 items) ====
printf 'OHOS-2 varargs conversion, formatted output in %s\n' "$DBG"

rm -f "$DBG"
ifindex -x21 -I "$CFG" </dev/null >"$WORK/ix3.out" 2>"$WORK/ix3.err"
rc=$?
if [ "$rc" = 0 ]; then
    ok "OHOS-2a ifindex -x21 exits 0 (verbose 2^21-1)"
else
    bad "OHOS-2a ifindex -x21: rc=$rc (expected 0)"
    diag "$WORK/ix3.err"
fi

# start line: debug(0,"start %s ver %s of %s, verbose 0x%08lx", ...) - four
# arguments, the last one an unsigned long. Only the stable halves are
# asserted; the middle is the build timestamp from the generated version.c.
assert_line "OHOS-2b start line, first %s arguments" "$DBG" \
    "start ifindex ver 2.14-tx8.10 of "
assert_line "OHOS-2c start line, unsigned long argument through %08lx" "$DBG" \
    ", verbose 0x001fffff"
# debug(20,"Initialize %d nodelists", n)
assert_line "OHOS-2d int argument through %d" "$DBG" "Initialize 1 nodelists"
# debug(20,"opened nodelist \"%s\"", ...)
assert_line "OHOS-2e string argument through %s" "$DBG" \
    "opened nodelist \"$NLD/nodelist.266\""
# debug(21,"put: %u:%u/%u.%u as (%u,%lu)", zone,net,node,point,i,off) - six
# arguments, the offsets being the fixture line starts 135 and 266.
assert_line "OHOS-2f six-argument call, node entry at offset 135" "$DBG" \
    "put: 2:5020/230.0 as (0,135)"
assert_line "OHOS-2g six-argument call, point entry at offset 266" "$DBG" \
    "put: 2:5020/230.1 as (0,266)"

# ------------------------------------------------------------------ summary
TOTAL=$((PASS + FAIL))
printf 'HARMONYOS-SPECIFIC TESTS: %d/%d check items passed (OHOS-1 ndbm/libgdbm_compat, OHOS-2 varargs->stdarg)\n' \
    "$PASS" "$TOTAL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
