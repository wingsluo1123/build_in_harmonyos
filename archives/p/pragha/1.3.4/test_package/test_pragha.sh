#!/bin/sh
# test_pragha.sh — headless verification of the packaged pragha binary.
#
# pragha is a GTK3 GUI music player and HarmonyOS PC has no X server. These
# tests cover every headless-verifiable surface of the installed binary:
#   1. upstream CLI contract: --version / --help;
#   2. the adaptation's new HarmonyOS consumer case --selftest (production
#      checks: musicobject round trip/dup/compare, playlist format
#      detection, sqlite3 and GStreamer runtime binding);
#   3. the no-display failure path, proving the binary actually loads and
#      initialises the GTK3/GLib libraries it links.
set -eu

pragha_bin="$1"
work_root=${TMPDIR:-$PWD}
# Keep the no-display launch log for post-mortem evidence (no rm cleanup:
# some worker PATHs carry broken rm wrappers that would fail the script
# at trap time with exit 126).
log="$work_root/pragha-test-no-display-$$.log"

asserts=0
failures=0

assert_cond() {
    label=$1
    shift
    asserts=$((asserts + 1))
    if "$@" >/dev/null 2>&1; then
        printf 'pragha-assert: %s: PASS\n' "$label"
    else
        printf 'pragha-assert: %s: FAIL\n' "$label"
        failures=$((failures + 1))
    fi
}

assert_grep() {
    asserts=$((asserts + 1))
    if printf '%s' "$2" | grep -qF -- "$3"; then
        printf 'pragha-assert: %s: PASS\n' "$1"
    else
        printf 'pragha-assert: %s: FAIL\n' "$1"
        failures=$((failures + 1))
    fi
}

assert_igrep() {
    asserts=$((asserts + 1))
    if printf '%s' "$2" | grep -qiF -- "$3"; then
        printf 'pragha-assert: %s: PASS\n' "$1"
    else
        printf 'pragha-assert: %s: FAIL\n' "$1"
        failures=$((failures + 1))
    fi
}

assert_eq() {
    asserts=$((asserts + 1))
    if [ "$2" = "$3" ]; then
        printf 'pragha-assert: %s: PASS\n' "$1"
    else
        printf 'pragha-assert: %s: FAIL (expected [%s], got [%s])\n' "$1" "$3" "$2"
        failures=$((failures + 1))
    fi
}

# --- package presence ---------------------------------------------------
assert_cond binary-exists test -f "$pragha_bin"
assert_cond binary-executable test -x "$pragha_bin"

# --- upstream CLI contract (headless) -----------------------------------
version_output=$("$pragha_bin" --version 2>&1) || true
assert_eq version-rc0 "$("$pragha_bin" --version >/dev/null 2>&1; echo $?)" 0
assert_grep version-banner "$version_output" "pragha 1.3.4"

help_output=$("$pragha_bin" --help 2>&1) || true
assert_eq help-rc0 "$("$pragha_bin" --help >/dev/null 2>&1; echo $?)" 0
assert_grep help-usage "$help_output" "Usage:"
assert_grep help-selftest-option "$help_output" "--selftest"

# --- adaptation HarmonyOS consumer case: --selftest ---------------------
set +e
selftest_output=$("$pragha_bin" --selftest 2>&1)
selftest_rc=$?
set -e
assert_eq selftest-rc0 "$selftest_rc" 0
assert_grep selftest-summary "$selftest_output" "all checks passed"
assert_igrep selftest-glib-line "$selftest_output" "glib 2."
assert_grep selftest-sqlite-line "$selftest_output" "sqlite3 3."
assert_grep selftest-gstreamer-line "$selftest_output" "GStreamer"

# --- GUI cannot open a display on OHOS: must fail closed ---------------
# This exit path is reached only after GTK3/GLib were loaded and the GTK
# display initialisation ran, so it doubles as a library-linkage proof.
set +e
"$pragha_bin" >"$log" 2>&1
no_display_rc=$?
set -e
asserts=$((asserts + 1))
if [ "$no_display_rc" -ne 0 ]; then
    printf 'pragha-assert: no-display-nonzero: PASS\n'
else
    printf 'pragha-assert: no-display-nonzero: FAIL (rc 0)\n'
    failures=$((failures + 1))
fi
assert_igrep no-display-diagnostic "$(cat "$log")" "cannot open display"

printf 'pragha-test: %s assertions, %s failures\n' "$asserts" "$failures"
if [ "$failures" -ne 0 ]; then
    exit 1
fi
exit 0
