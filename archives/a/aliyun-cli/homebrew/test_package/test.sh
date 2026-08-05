#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-aliyun>" >&2
    exit 2
fi

aliyun_bin="$1"

if [ ! -f "$aliyun_bin" ]; then
    echo "aliyun binary not found: $aliyun_bin" >&2
    exit 1
fi

# Test 1: version output should contain "3.0.229"
version_output="$("$aliyun_bin" version)"
printf '%s\n' "$version_output" | grep -F "3.0.229" >/dev/null

# Test 2: help should exit cleanly
"$aliyun_bin" help >/dev/null 2>&1

echo "All tests passed."
