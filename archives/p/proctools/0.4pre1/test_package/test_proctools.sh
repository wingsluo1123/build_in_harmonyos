#!/usr/bin/env bash
set -euo pipefail

package_folder="$1"
bin_dir="$package_folder/bin"

for program in pgrep pkill pfind; do
    test -x "$bin_dir/$program"
    "$bin_dir/$program" -V | grep -q "0.4pre1"
done

assert_invalid_signal() {
    local argument="$1"
    local output
    local status

    if output=$("$bin_dir/pkill" -s "$argument" proctools-no-such-process 2>&1); then
        status=0
    else
        status=$?
    fi

    test "$status" -eq 64
    grep -q "invalid signal number: $argument" <<<"$output"
}

assert_invalid_signal "not-a-number"
assert_invalid_signal "9junk"
assert_invalid_signal "-1"
assert_invalid_signal "999999999999999999999999"

echo "proctools binaries, version output, and signal validation tests passed"
