#!/usr/bin/env bash
# test_package/test.sh — Run aliyun version and validate output matches 3.4.11
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

"$aliyun_bin" version >/dev/null
version_output="$("$aliyun_bin" version)"

printf '%s\n' "$version_output" | grep -F "3.4.11" >/dev/null
