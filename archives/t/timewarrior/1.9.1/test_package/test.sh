#!/bin/sh
set -eu
output=$("$1" --version 2>&1)
printf '%s\n' "$output" | grep -E "1\.9\.1|timew|Timewarrior"
