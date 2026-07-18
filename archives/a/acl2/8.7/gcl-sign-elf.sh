#!/bin/bash
set -euo pipefail

target="$1"
objcopy=/data/service/hnp/bin/llvm-objcopy
signer=/data/service/hnp/bin/binary-sign-tool
target_dir=$(dirname "$target")
temp_dir=$(mktemp -d "$target_dir/.gcl-sign.XXXXXX")
signed="$temp_dir/signed"
trap 'rm -rf "$temp_dir"' EXIT

if "$objcopy" --dump-section .codesign=/dev/null "$target" 2>/dev/null; then
    "$objcopy" --remove-section .codesign "$target"
fi
"$signer" sign -inFile "$target" -outFile "$signed" -selfSign 1
mv "$signed" "$target"
chmod 755 "$target"
