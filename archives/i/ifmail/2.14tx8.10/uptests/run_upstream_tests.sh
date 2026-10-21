#!/bin/sh
# run_upstream_tests.sh - execute ifmail's upstream -DTESTING self-tests.
#
# Counting unit (the single unit used in MANIFEST.yml, notes.md, the build log
# and both PR tables): INDEPENDENT CHECK ITEMS. Every assert_* call below is
# one independently pass/fail-able item.
#
# iflib/Makefile ships four -DTESTING targets:
#   testconf    (rdconfig.c)  config-file parser trace        -> executed
#   testscan    (scanout.c)   outbound directory scanner      -> executed
#   testrfcaddr (rfcaddr.c)   RFC-822 address parser          -> executed
#   testtrap    (trap.c)      signal handler against a fault  -> NOT executed
# testtrap is excluded deliberately, not skipped for convenience: under
# -DTESTING its handler prints a newline and returns instead of calling
# abort(), so the faulting store re-executes and the program has no
# deterministic terminal state. Reference measurement (macOS/arm64, same
# patched sources): rc=133 with zero bytes of output. It is declared as
# 0 check items rather than dressed up as a pass.
#
# Where the expected values come from (expectations must be derivable from the
# inputs, never hand-waved):
#   * config.tmpl - the "<cfg>(N)" prefixes are the literal line numbers of the
#     committed template (address=1 ... domtrans=7, debugfile=8);
#   * outbound/139c00e6.out and .flo - FTS-0032 names: 0x139c=5020 (net),
#     0x00e6=230 (node), so scanout() must decode them to 2:5020/230 and
#     classify .out as a packet and .flo as a flo file;
#   * rfcaddr.txt - 6 addresses; target/remainder/comment follow
#     parserfcaddr()'s own branches ("anything@somewhere", "domain!something",
#     "remainder only present").
# All expected strings were captured from a reference build of the same patched
# sources and re-derived by hand from the fixtures above.
#
# Failure diagnostics (captured stream + workdir listing) are printed by the
# assert helpers and never influence the verdict.
#
# Usage: run_upstream_tests.sh [workdir]
#   workdir defaults to ./uptests-work (never /tmp: HMDFS /tmp is read-only).

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
IFLIB_DIR=$(cd "$SCRIPT_DIR/../iflib" && pwd)
WORK=${1:-$PWD/uptests-work}

PASS=0
FAIL=0

diag() {
    printf '    --- diagnostics: captured output (%s) ---\n' "$1"
    sed -n '1,60p' "$1" 2>/dev/null | sed 's/^/    | /'
    printf '    --- diagnostics: %s listing ---\n' "$WORK"
    ls -laR "$WORK" 2>/dev/null | sed -n '1,40p' | sed 's/^/    | /'
}

assert_rc() { # <label> <actual> <expected>
    if [ "$2" = "$3" ]; then
        PASS=$((PASS + 1)); printf '  [pass] %s (rc=%s)\n' "$1" "$2"
    else
        FAIL=$((FAIL + 1))
        printf '  [FAIL] %s: rc=%s, expected %s\n' "$1" "$2" "$3"
    fi
}

assert_line() { # <label> <file> <fixed-string>
    if grep -qF -- "$3" "$2" 2>/dev/null; then
        PASS=$((PASS + 1)); printf '  [pass] %s\n' "$1"
    else
        FAIL=$((FAIL + 1)); printf '  [FAIL] %s: missing %s\n' "$1" "$3"
        diag "$2"
    fi
}

for t in testconf testscan testrfcaddr; do
    if [ ! -x "$IFLIB_DIR/$t" ]; then
        printf 'FATAL: %s/%s not built (the recipe builds it first)\n' \
            "$IFLIB_DIR" "$t"
        exit 2
    fi
done

# --------------------------------------------------------------- fixtures
rm -rf "$WORK"
mkdir -p "$WORK/spool/inb" "$WORK/spool/outb" "$WORK/spool/nl.d" || exit 2
cp "$SCRIPT_DIR"/outbound/* "$WORK/spool/outb/" || exit 2
sed "s|@WORKDIR@|$WORK|g" "$SCRIPT_DIR/config.tmpl" > "$WORK/config" || exit 2

CFG="$WORK/config"
OUTB="$WORK/spool/outb"
DBG="$WORK/ifdebug"

# ------------------------------------------------------ testconf (8 items)
printf 'testconf: config parser trace over %s\n' "$CFG"
"$IFLIB_DIR/testconf" "$CFG" >"$WORK/testconf.out" 2>"$WORK/testconf.err"
assert_rc "testconf: exit status" "$?" 0
assert_line "testconf: address keyword parsed (line 1)" "$WORK/testconf.err" \
    "$CFG(1): \"address\" \"2:5020/230@fidonet\" - parsed"
assert_line "testconf: getaddr decodes the FTN address" "$WORK/testconf.err" \
    "getaddr: $CFG(1): address 2:5020/230@fidonet"
assert_line "testconf: getstr stores myfqdn (line 2)" "$WORK/testconf.err" \
    "getstr: $CFG(2): myfqdn fido.example.org"
assert_line "testconf: getadnl registers the nodelist (line 9)" "$WORK/testconf.err" \
    "getadnl: $CFG(9): nodelist $WORK/spool/nl.d/nodelist"
assert_line "testconf: getdtrn splits the domtrans pair (line 11)" "$WORK/testconf.err" \
    "getdtrn: $CFG(11): expr \".fidonet\" line \".ftn\""
assert_line "testconf: summary block printed" "$WORK/testconf.err" \
    "globals set in rdconfig:"
assert_line "testconf: configname recorded" "$WORK/testconf.err" \
    "configname: $CFG"

# ------------------------------------------------------ testscan (9 items)
printf 'testscan: outbound scanner over %s\n' "$OUTB"
"$IFLIB_DIR/testscan" "$CFG" >"$WORK/testscan.out" 2>"$WORK/testscan.err"
assert_rc "testscan: exit status" "$?" 0
# readconfig() freopen()s stderr onto debugfile, so the scan trace is in $DBG.
assert_line "testscan: domain taken from config" "$DBG" \
    "checking domain fidonet"
assert_line "testscan: outbound directory entered" "$DBG" \
    "enter scan_dir \"$OUTB\" (node)"
assert_line "testscan: FTS name recognised (12 chars, dot at index 8)" "$DBG" \
    "checking: \"139c00e6.out\""
assert_line "testscan: .out classified as a packet" "$DBG" \
    "packet \"139c00e6.out\""
assert_line "testscan: net/node hex decoded to 2:5020/230, flavor o" "$DBG" \
    "addr \"2:5020/230@fidonet\" flavor 'o', pkt, name \"$OUTB/139c00e6.out\""
assert_line "testscan: .flo classified as a flo file" "$DBG" \
    "flo file \"139c00e6.flo\""
assert_line "testscan: flo entry reported with the same address" "$DBG" \
    "addr \"2:5020/230@fidonet\" flavor 'o', flo, name \"$OUTB/139c00e6.flo\""
assert_line "testscan: scanout returned 0" "$DBG" "scanout rc=0"

# -------------------------------------------------- testrfcaddr (13 items)
printf 'testrfcaddr: RFC-822 address parser over %s\n' "$SCRIPT_DIR/rfcaddr.txt"
"$IFLIB_DIR/testrfcaddr" <"$SCRIPT_DIR/rfcaddr.txt" \
    >"$WORK/testrfcaddr.out" 2>&1
assert_rc "testrfcaddr: exit status" "$?" 0
assert_line "testrfcaddr: user@domain -> target" "$WORK/testrfcaddr.out" \
    "   target: \"domain\""
assert_line "testrfcaddr: user@domain -> remainder" "$WORK/testrfcaddr.out" \
    "remainder: \"user\""
assert_line "testrfcaddr: angle address -> target" "$WORK/testrfcaddr.out" \
    "   target: \"domain.org\""
assert_line "testrfcaddr: angle address -> remainder" "$WORK/testrfcaddr.out" \
    "remainder: \"john\""
assert_line "testrfcaddr: angle address -> comment kept" "$WORK/testrfcaddr.out" \
    "  comment: \"John Smith \""
assert_line "testrfcaddr: quoted name and comment -> target" "$WORK/testrfcaddr.out" \
    "   target: \"x.org\""
assert_line "testrfcaddr: quoted name and comment -> remainder" "$WORK/testrfcaddr.out" \
    "remainder: \"js\""
assert_line "testrfcaddr: percent gateway -> target" "$WORK/testrfcaddr.out" \
    "   target: \"gateway\""
assert_line "testrfcaddr: percent gateway -> remainder" "$WORK/testrfcaddr.out" \
    "remainder: \"john%site\""
assert_line "testrfcaddr: UUCP bang path -> target" "$WORK/testrfcaddr.out" \
    "   target: \"uucphost\""
assert_line "testrfcaddr: UUCP bang path -> remainder" "$WORK/testrfcaddr.out" \
    "remainder: \"subhost!user\""
assert_line "testrfcaddr: bare local user -> remainder only" "$WORK/testrfcaddr.out" \
    "remainder: \"plainuser\""

# ----------------------------------------------------------------- summary
TOTAL=$((PASS + FAIL))
printf 'UPSTREAM TESTS: %d/%d check items passed (testconf + testscan + testrfcaddr; testtrap excluded, see header)\n' \
    "$PASS" "$TOTAL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
