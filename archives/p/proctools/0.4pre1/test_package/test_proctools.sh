#!/bin/sh
set -eu

package_folder="$1"
bin_dir="$package_folder/bin"

for program in pgrep pkill pfind; do
    test -x "$bin_dir/$program"
    "$bin_dir/$program" -V | grep -q "0.4pre1"
done

echo "proctools binaries and version output tests passed"
