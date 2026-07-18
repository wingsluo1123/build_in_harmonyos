#!/bin/bash
set -euo pipefail

target="$1"
objcopy=/data/service/hnp/bin/llvm-objcopy
signer=/data/service/hnp/bin/binary-sign-tool
signed="${target}.signed.tmp"

"$objcopy" --remove-section .codesign "$target"
"$signer" sign -inFile "$target" -outFile "$signed" -selfSign 1
mv "$signed" "$target"
chmod 755 "$target"
