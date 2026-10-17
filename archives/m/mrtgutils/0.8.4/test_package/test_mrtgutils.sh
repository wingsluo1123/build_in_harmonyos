#!/usr/bin/env sh
set -eu

BIN=${MRTGUTILS_BIN:?MRTGUTILS_BIN is required}
WORK=${MRTGUTILS_WORK:?MRTGUTILS_WORK is required}
RESULT=${MRTGUTILS_RESULT:?MRTGUTILS_RESULT is required}

rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

passed=0
check() {
    passed=$((passed + 1))
    printf '[ok] %s\n' "$1"
}

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

is_uint() {
    case "${1:-}" in
        ''|*[!0-9]*) return 1 ;;
        *) return 0 ;;
    esac
}

read_two_numeric() {
    first=
    second=
    {
        IFS= read -r first || true
        IFS= read -r second || true
    } < "$1"
    is_uint "$first" && is_uint "$second"
}

for program in mrtg-load mrtg-uptime mrtg-ip-acct mrtg-apache mrtg-sensors; do
    [ -x "$BIN/$program" ] || fail "installed executable is missing: $BIN/$program"
done
check 'all five installed executables are present'

"$BIN/mrtg-uptime" -t sys -u s >"$WORK/uptime.out" 2>&1
read_two_numeric "$WORK/uptime.out" || fail 'mrtg-uptime did not emit two numeric values'
check 'mrtg-uptime emits two numeric values from the target runtime'

"$BIN/mrtg-load" -l 1 >"$WORK/load.out" 2>&1
read_two_numeric "$WORK/load.out" || fail 'mrtg-load -l 1 did not emit two numeric values'
check 'mrtg-load -l 1 emits two numeric values with valid storage'

"$BIN/mrtg-load" -l 5 >"$WORK/load5.out" 2>&1
read_two_numeric "$WORK/load5.out" || fail 'mrtg-load -l 5 did not emit two numeric values'
check 'mrtg-load -l 5 selects the five-minute average'

if "$BIN/mrtg-load" -l 7 >"$WORK/load-invalid.out" 2>&1; then
    fail 'mrtg-load -l 7 unexpectedly succeeded'
fi
if ! grep -q "unknown load average period '7'" "$WORK/load-invalid.out" ||
   ! grep -q 'possible periods are 1, 5, and 15' "$WORK/load-invalid.out"; then
    fail 'mrtg-load -l 7 did not report the documented error'
fi
check 'mrtg-load -l 7 rejects an unknown period with the documented diagnostic'

"$BIN/mrtg-ip-acct" lo >"$WORK/ip-acct.out" 2>&1
read_two_numeric "$WORK/ip-acct.out" || fail 'mrtg-ip-acct did not emit two numeric values'
check 'mrtg-ip-acct emits interface counters with the portable format'

if "$BIN/mrtg-apache" >"$WORK/apache.out" 2>&1; then
    fail 'mrtg-apache without a hostname unexpectedly succeeded'
fi
if ! grep -q 'Usage: mrtg-apache' "$WORK/apache.out"; then
    fail 'mrtg-apache did not print its usage on the invalid invocation'
fi
check 'mrtg-apache rejects an invocation without a hostname and prints usage'

if "$BIN/mrtg-sensors" >"$WORK/sensors.out" 2>&1; then
    fail 'mrtg-sensors without chip and label arguments unexpectedly succeeded'
fi
if ! grep -q 'Usage: mrtg-sensors' "$WORK/sensors.out"; then
    fail 'mrtg-sensors did not print its usage on the invalid invocation'
fi
check 'mrtg-sensors rejects an invocation without chip/label arguments and prints usage'

printf 'mrtgutils smoke: %s passed\n' "$passed" >"$RESULT"
