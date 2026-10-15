#!/usr/bin/env bash
# test_package driver — compiles and runs the Java consumer tests against the
# packaged TuxGuitar JARs (libexec/*.jar) on the HarmonyOS device.
set -euo pipefail

PKG_FOLDER="${1:?usage: test.sh <package_folder>}"
LIBDIR="$PKG_FOLDER/libexec"

echo "package folder : $PKG_FOLDER"
echo "jar directory  : $LIBDIR"

[ -d "$LIBDIR" ] || { echo "FAIL: libexec/ not found in package"; exit 1; }

shopt -s nullglob
JARS=("$LIBDIR"/*.jar)
shopt -u nullglob
[ "${#JARS[@]}" -gt 0 ] || { echo "FAIL: no JAR files in $LIBDIR"; exit 1; }
echo "jars           : ${#JARS[@]}"
for j in "${JARS[@]}"; do echo "   - $(basename "$j")"; done

# tuxguitar-lib must be present in the package
ls "$LIBDIR"/tuxguitar-lib-*.jar >/dev/null 2>&1 \
    || { echo "FAIL: tuxguitar-lib-*.jar missing from package"; exit 1; }

CP="$(IFS=:; echo "${JARS[*]}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$(mktemp -d)"

echo "--- javac ---"
javac -encoding UTF-8 -cp "$CP" -d "$OUT" \
    "$SCRIPT_DIR/TestTuxGuitarCore.java" \
    "$SCRIPT_DIR/TestHarmonyOSPlatform.java"

echo "--- TestTuxGuitarCore ---"
java -cp "$CP:$OUT" TestTuxGuitarCore

echo "--- TestHarmonyOSPlatform ---"
java -cp "$CP:$OUT" TestHarmonyOSPlatform

rm -rf "$OUT"
echo "ALL TEST_PACKAGE TESTS PASSED"
