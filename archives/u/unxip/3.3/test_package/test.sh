#!/system/bin/sh
set -eu

output="$(unxip --version)"
printf '%s\n' "$output"
test "$output" = "unxip 3.3"
