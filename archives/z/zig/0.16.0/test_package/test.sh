#!/usr/bin/env sh
set -eu

zig_bin=$1
source_file=$2
work_dir=$3

version=$("$zig_bin" version)
if [ "$version" != "0.16.0" ]; then
    echo "unexpected Zig version: $version" >&2
    exit 1
fi

mkdir -p "$work_dir"
cd "$work_dir"

"$zig_bin" build-exe "$source_file" -O ReleaseSmall --name smoke

if command -v llvm-objcopy >/dev/null 2>&1; then
    llvm-objcopy --remove-section .codesign ./smoke 2>/dev/null || true
fi
if command -v binary-sign-tool >/dev/null 2>&1; then
    binary-sign-tool sign -inFile ./smoke -outFile ./smoke -selfSign 1
fi

./smoke
