#!/data/service/hnp/bin/bash
set -eu

output="$(nymphcast_server --version)"
printf '%s\n' "$output"
printf '%s\n' "$output" | grep -F "NymphCast version"
