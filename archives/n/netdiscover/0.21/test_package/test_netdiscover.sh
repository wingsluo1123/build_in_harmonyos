#!/bin/sh
set -u

output=$("$1" -h 2>&1 || true)
printf '%s\n' "$output" | grep "Netdiscover 0.21"
printf '%s\n' "$output" | grep "Usage:"
