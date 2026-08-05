#!/bin/bash
# test_package/test.sh — verify bishengjdk adaptation was applied correctly
# Checks that ELF patching, glibc compat shim, musl symlinks, and signing
# were all applied to the pre-built JDK binary.
set -eu

# Find the java binary from the installed package (conanrun sets PATH)
JAVA_BIN=""
if command -v java &>/dev/null; then
    JAVA_BIN=$(command -v java)
fi

# Try JAVA_HOME
if [ -z "$JAVA_BIN" ] && [ -n "${JAVA_HOME:-}" ]; then
    if [ -f "$JAVA_HOME/bin/java" ]; then
        JAVA_BIN="$JAVA_HOME/bin/java"
    fi
fi

# Search in conan cache
if [ -z "$JAVA_BIN" ]; then
    for base in "$HOME/.conan2" "$HOME/.conan"; do
        found=$(find "$base" -path "*/bishengjdk/*/bin/java" -type f 2>/dev/null | head -1)
        if [ -n "$found" ]; then
            JAVA_BIN="$found"
            break
        fi
    done
fi

if [ -z "$JAVA_BIN" ]; then
    echo "[fail] java binary not found in package"
    exit 1
fi

echo "[step] Testing: $JAVA_BIN"
JDK_HOME=$(dirname "$JAVA_BIN")
JDK_HOME=$(dirname "$JDK_HOME")

READELF="${READELF:-readelf}"
if ! command -v "$READELF" &>/dev/null; then
    READELF="/data/service/hnp/bin/readelf"
fi

# Check 1: java binary is an ELF
if ! file "$JAVA_BIN" 2>/dev/null | grep -q "ELF"; then
    echo "[fail] java binary is not an ELF file"
    exit 1
fi
echo "[ok] java binary is ELF"

# Check 2: interpreter patched to musl (glibc-to-musl adaptation)
interp=$("$READELF" -l "$JAVA_BIN" 2>/dev/null | grep "interpreter" || true)
if echo "$interp" | grep -q "ld-musl-aarch64"; then
    echo "[ok] interpreter patched to musl"
elif echo "$interp" | grep -q "ld-linux-aarch64"; then
    echo "[fail] interpreter NOT patched (still glibc ld-linux)"
    exit 1
fi

# Check 3: glibc NEEDED entries replaced (no libc.so.6)
needed=$("$READELF" -d "$JAVA_BIN" 2>/dev/null | grep "NEEDED" || true)
if echo "$needed" | grep -q "libc.so.6"; then
    echo "[fail] glibc NEEDED entry libc.so.6 still present"
    exit 1
fi
echo "[ok] glibc NEEDED entries replaced"

# Check 4: glibc compat shim exists (libgcompat.so)
if [ -f "$JDK_HOME/lib/libgcompat.so" ]; then
    echo "[ok] glibc compat shim found"
else
    echo "[fail] glibc compat shim not found"
    exit 1
fi

# Check 5: musl compat library exists (libc.so -> musl ld, may be symlink or copy)
if [ -e "$JDK_HOME/lib/libc.so" ]; then
    echo "[ok] musl compat library found: libc.so"
else
    echo "[fail] musl compat library libc.so not found"
    exit 1
fi

# Check 6: binary self-signed (.codesign section present)
codesign=$("$READELF" -S "$JAVA_BIN" 2>/dev/null | grep "codesign" || true)
if [ -n "$codesign" ]; then
    echo "[ok] binary self-signed (.codesign section present)"
else
    echo "[fail] binary not signed (no .codesign section)"
    exit 1
fi

echo "[ok] All adaptation checks passed"
