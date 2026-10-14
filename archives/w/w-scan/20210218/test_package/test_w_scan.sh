#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
    printf 'usage: %s RESULT_FILE\n' "$0" >&2
    exit 2
fi

result_file=$1
binary=${W_SCAN_BIN:-w_scan}
result_dir=$(dirname "$result_file")
tmpdir="$result_dir/w-scan-test-data"
rm -rf "$tmpdir"
mkdir -p "$tmpdir"
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
passed=0

check() {
    passed=$((passed + 1))
    printf '[ok] %s\n' "$1"
}

command -v "$binary" >"$tmpdir/binary-path.txt" 2>/dev/null || {
    printf 'w_scan is not available on PATH\n' >&2
    exit 1
}
binary=$(cat "$tmpdir/binary-path.txt")
test -x "$binary" || {
    printf 'w_scan is not executable: %s\n' "$binary" >&2
    exit 1
}
check 'installed w_scan is executable'

"$binary" -V >"$tmpdir/version.txt" 2>&1
grep -qx '20210218' "$tmpdir/version.txt"
check 'short version output reports 20210218'

"$binary" --help >"$tmpdir/help.txt" 2>&1
grep -q 'usage: w_scan' "$tmpdir/help.txt"
check 'basic help prints usage'

"$binary" -h >"$tmpdir/short-help.txt" 2>&1
grep -q 'usage: w_scan' "$tmpdir/short-help.txt"
check 'short help alias prints usage'

"$binary" --extended-help >"$tmpdir/extended-help.txt" 2>&1
grep -q 'expert help' "$tmpdir/extended-help.txt"
check 'extended help is available'

"$binary" --country '?' >"$tmpdir/countries.txt" 2>&1
grep -q 'AFGHANISTAN' "$tmpdir/countries.txt"
check 'country discovery lists countries'

"$binary" --satellite '?' >"$tmpdir/satellites.txt" 2>&1
grep -q 'S19E2' "$tmpdir/satellites.txt"
check 'satellite discovery lists satellites'

if "$binary" --definitely-invalid >"$tmpdir/invalid.txt" 2>&1; then
    printf 'unknown option unexpectedly succeeded\n' >&2
    exit 1
fi
grep -q 'usage:' "$tmpdir/invalid.txt"
check 'unknown option is rejected with usage'

printf 'w_scan smoke: %s passed\n' "$passed" >"$result_file"
