#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for the emlog user-space tools.
# Runs in the conanrun env (PATH includes the installed bin/ dir).
set -u

FAIL=0
chk() { # $1=name $2=result $3=detail
    if [ "$2" = "0" ]; then
        printf 'PASS: %s\n' "$1"
    else
        printf 'FAIL: %s%s\n' "$1" "${3:+ -- $3}"
        FAIL=1
    fi
}

WORK="${TMPDIR:-/data/local/tmp}/emlog-consumer-$$"
mkdir -p "$WORK" || WORK="/tmp/emlog-consumer-$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

# 1) A small regular file is copied byte-for-byte through the non-blocking path.
printf 'hello emlog\n' > "$WORK/small.in"
nbcat "$WORK/small.in" > "$WORK/small.out" 2>"$WORK/small.err"
rc=$?
if [ "$rc" = "0" ] && cmp -s "$WORK/small.in" "$WORK/small.out"; then
    chk "nbcat copies a regular file" 0
else
    chk "nbcat copies a regular file" 1 "rc=$rc"
fi

# 2) Empty input must produce empty output and succeed.
: > "$WORK/empty.in"
nbcat "$WORK/empty.in" > "$WORK/empty.out" 2>"$WORK/empty.err"
rc=$?
if [ "$rc" = "0" ] && [ ! -s "$WORK/empty.out" ]; then
    chk "nbcat preserves empty input" 0
else
    chk "nbcat preserves empty input" 1 "rc=$rc"
fi

# 3) Binary data, including NUL bytes, must not be transformed.
printf 'alpha\0beta\n' > "$WORK/binary.in"
nbcat "$WORK/binary.in" > "$WORK/binary.out" 2>"$WORK/binary.err"
rc=$?
if [ "$rc" = "0" ] && cmp -s "$WORK/binary.in" "$WORK/binary.out"; then
    chk "nbcat preserves binary data" 0
else
    chk "nbcat preserves binary data" 1 "rc=$rc"
fi

# 4) Input larger than nbcat's 4096-byte stack buffer must be copied in full.
: > "$WORK/large.in"
i=0
while [ "$i" -lt 600 ]; do
    printf 'record-%03d-0123456789\n' "$i" >> "$WORK/large.in"
    i=$((i + 1))
done
nbcat "$WORK/large.in" > "$WORK/large.out" 2>"$WORK/large.err"
rc=$?
if [ "$rc" = "0" ] && cmp -s "$WORK/large.in" "$WORK/large.out"; then
    chk "nbcat drains input larger than one buffer" 0
else
    chk "nbcat drains input larger than one buffer" 1 "rc=$rc"
fi

# 5) A missing input is a real error and reports the path.
if nbcat "$WORK/missing" >"$WORK/missing.out" 2>"$WORK/missing.err"; then
    chk "nbcat rejects a missing input" 1 "unexpected success"
elif [ -s "$WORK/missing.err" ]; then
    chk "nbcat rejects a missing input" 0
else
    chk "nbcat rejects a missing input" 1 "no diagnostic"
fi

# 6) nbcat without arguments prints usage and exits non-zero.
if nbcat >"$WORK/nbcat-usage.out" 2>&1; then
    chk "nbcat no-arg usage" 1 "unexpected success"
elif grep -q 'usage: nbcat' "$WORK/nbcat-usage.out"; then
    chk "nbcat no-arg usage" 0
else
    chk "nbcat no-arg usage" 1 "usage text missing"
fi

# 7) mkemlog without arguments prints usage and exits non-zero.
if mkemlog >"$WORK/mkemlog-usage.out" 2>&1; then
    chk "mkemlog no-arg usage" 1 "unexpected success"
elif grep -q 'usage: mkemlog' "$WORK/mkemlog-usage.out"; then
    chk "mkemlog no-arg usage" 0
else
    chk "mkemlog no-arg usage" 1 "usage text missing"
fi

# 8) Exercise mkemlog's platform boundary. On OHOS the kernel module is
# absent, so the patched error path must fail with the module diagnostic.
mkemlog_output=$(mkemlog "$WORK/emlog-device" 1 2>&1)
rc=$?
if [ "$rc" = "0" ]; then
    if [ -c "$WORK/emlog-device" ]; then
        chk "mkemlog creates the device when the module is loaded" 0
        rm -f "$WORK/emlog-device"
    else
        chk "mkemlog creates the device when the module is loaded" 1 "device node missing"
    fi
else
    case "$mkemlog_output" in
        *'Emlog module not loaded'*)
            chk "mkemlog reports the missing kernel module" 0
            ;;
        *)
            chk "mkemlog reports the missing kernel module" 1 "rc=$rc output=$mkemlog_output"
            ;;
    esac
fi

if [ "$FAIL" = "0" ]; then
    printf 'RESULT: consumer assertions passed\n'
    exit 0
fi
printf 'RESULT: consumer assertions FAILED\n'
exit 1
