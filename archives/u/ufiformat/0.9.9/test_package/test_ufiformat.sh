#!/bin/sh
# test_ufiformat.sh — functional tests for the packaged ufiformat binary.
#
# Every case really executes bin/ufiformat (R34): help output, argument
# contract (non-zero exits with diagnostics) and hardware-free device
# listing. Real USB-FDD formatting needs physical hardware unavailable on
# CI/true-machine, so it is honestly out of scope (see notes.md R40 note).
#
# Output contract (single deterministic source for counters):
#   one "[ok] <name>" / "[FAIL] <name> <detail>" ledger line per case,
#   plus exactly one summary line:
#     RESULT: <passed> passed, <failed> failed
# The conanfile parses ONLY the RESULT line (no stdout word counting).
set -eu

BIN="${UFIFORMAT_BIN:-ufiformat}"
TMPD="${TMPDIR:-/tmp}/ufiformat-test-$$"
mkdir -p "$TMPD"

pass_count=0
fail_count=0

report_ok() {
    pass_count=$((pass_count + 1))
    echo "[ok] $1"
}

report_fail() {
    fail_count=$((fail_count + 1))
    echo "[FAIL] $1 :: $2"
}

# run_case <name> <expected_rc> <expected_substring> <stream: out|err> -- <args...>
# rc expectation: "0" exact zero, "nonzero" any non-zero.
run_case() {
    name="$1"; want_rc="$2"; want_text="$3"; stream="$4"; shift 4
    out_f="$TMPD/out.txt"; err_f="$TMPD/err.txt"
    : > "$out_f"; : > "$err_f"
    if "$BIN" "$@" >"$out_f" 2>"$err_f"; then
        rc=0
    else
        rc=$?
    fi
    if [ "$stream" = "err" ]; then
        text="$(cat "$err_f" "$out_f")"
    else
        text="$(cat "$out_f")"
    fi
    rc_ok=0
    if [ "$want_rc" = "0" ]; then
        [ "$rc" -eq 0 ] && rc_ok=1
    else
        [ "$rc" -ne 0 ] && rc_ok=1
    fi
    case "$text" in
        *"$want_text"*) text_ok=1 ;;
        *) text_ok=0 ;;
    esac
    if [ "$rc_ok" -eq 1 ] && [ "$text_ok" -eq 1 ]; then
        report_ok "$name"
    else
        report_fail "$name" "rc=$rc rc_ok=$rc_ok text_ok=$text_ok"
    fi
}

echo "[step] ufiformat functional tests (BIN=$BIN)"

# 1-2: help paths exit 0 with non-empty, keyword-bearing output.
run_case "help-long" 0 "Usage:" out --help
run_case "help-short" 0 "-i, --inquire" out -h

# 3-5: argument contract — non-zero exit plus matching diagnostics.
run_case "no-device" nonzero "no device specified" err
run_case "bad-size" nonzero "format parameter should be numeric" err -f abc /dev/null
run_case "both-opts" nonzero "both inquire and format" err -f 1440 -i /dev/null

# 6: hardware-free listing exits 0 (empty set on OHOS, header still printed).
run_case "list-no-device" 0 "disk" out -i

# 7: inquiring a non-FDD node fails with a matching diagnostic.
# A temp regular file is used (not /dev/null): stat always succeeds and the
# node is deterministically neither sd nor sg, whatever /dev holds on OHOS.
echo "plain" > "$TMPD/plain.txt"
run_case "inquire-non-fdd" nonzero "device is not usb fdd" err -i "$TMPD/plain.txt"

echo "RESULT: $pass_count passed, $fail_count failed"
if [ "$fail_count" -ne 0 ]; then
    exit 1
fi
exit 0
