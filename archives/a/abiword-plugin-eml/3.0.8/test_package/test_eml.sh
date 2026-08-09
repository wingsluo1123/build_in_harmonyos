#!/bin/bash
# Verify the packaged abiword-plugin-eml plugin .so: valid ELF with ABI symbols.
# Usage: test_eml.sh <pkg_folder>
set -euo pipefail

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

# Locate eml plugin .so (keep full path)
SO=""
PLUGIN_DIR="$PKG_FOLDER/lib/abiword/plugins"
if [ -d "$PLUGIN_DIR" ]; then
    SO=$(find "$PLUGIN_DIR" -maxdepth 1 -name '*eml*.so' 2>/dev/null | head -1)
fi
if [ -z "$SO" ]; then
    SO=$(find "$PKG_FOLDER" -name '*eml*.so*' 2>/dev/null | head -1)
fi
if [ -z "$SO" ]; then
    echo "ERROR: EML plugin .so not found in package"
    exit 1
fi
echo "  [ok] plugin .so found: $SO"

# readelf: verify ELF + exported ABI symbols (hnp toolchain readelf preferred)
READELF=""
for cand in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf readelf; do
    if [ -x "$cand" ]; then
        READELF="$cand"
        break
    fi
done
if [ -z "$READELF" ]; then
    echo "ERROR: readelf not found"
    exit 1
fi
echo "  [ok] readelf: $READELF"

OUT=$($READELF -sW "$SO" 2>/dev/null) || { echo "ERROR: readelf failed"; exit 1; }

for sym in abi_plugin_register abi_plugin_unregister abi_plugin_supports_version; do
    if echo "$OUT" | grep -q "$sym"; then
        echo "  [ok] exported symbol: $sym"
    else
        echo "ERROR: expected symbol not found: $sym"
        exit 1
    fi
done

# Count FUNC symbols
func_count=$(echo "$OUT" | awk '$4=="FUNC"' | wc -l)
echo "  [ok] $func_count FUNC symbols exported"

echo "=== Results: 5 passed, 0 failed ==="
exit 0
