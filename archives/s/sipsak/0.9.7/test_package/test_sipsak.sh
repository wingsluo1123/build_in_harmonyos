#!/bin/sh
set -eu

package_folder="$1"
executable="$package_folder/bin/sipsak"

test -x "$executable"
"$executable" --version | grep -q "0.9.7"

echo "sipsak version test passed"
