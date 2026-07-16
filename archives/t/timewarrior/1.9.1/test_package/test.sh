#!/bin/sh
set -eu
"$1" --version 2>&1 | grep -E "1\.9\.1|timew|Timewarrior"
