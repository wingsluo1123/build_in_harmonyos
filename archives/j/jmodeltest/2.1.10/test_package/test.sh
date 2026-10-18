#!/bin/sh
# test_package consumer validation for jmodeltest 2.1.10 (HarmonyOS).
#
# Uses the packaged `jmodeltest` launcher. example-data files are shipped
# inside jModelTest.jar (javac+jar merged src/main/resources), so we extract
# one NEXUS alignment with the JDK jar tool to a writable dir and feed it to
# `-d <file> -getPhylip` (headless, no phyml binary required).
set -e
JMT="$1"
BUILD_DIR="$2"

echo "==> [1/3] structure check"
[ -f "$JMT" ] || { echo "FAIL: launcher missing"; exit 1; }
[ -x "$JMT" ] || { echo "FAIL: launcher not executable"; exit 1; }

# Find a java binary for extracting the example (the launcher locates its own JDK).
JAVA="$(command -v java || true)"
if [ -n "$JAVA" ]; then
  JAVA_BIN="$(command -v java)"
  JAR_TOOL="$(dirname "$JAVA_BIN")/jar"
fi
if [ -z "$JAVA_BIN" ] || [ ! -x "$JAR_TOOL" ]; then
  # try JDK dirs used by the launcher
  for j in "$HOME/bishengjdk17" "$HOME/usr/local/bishengjdk17" /usr/local/bishengjdk17; do
    if [ -x "$j/bin/java" ]; then JAR_TOOL="$j/bin/jar"; break; fi
  done
fi
[ -x "$JAR_TOOL" ] || { echo "FAIL: no JDK to extract example-data"; exit 1; }

LIBEXEC="$(cd "$(dirname "$JMT")/.." && pwd)/libexec"
JAR="$LIBEXEC/jModelTest.jar"
[ -f "$JAR" ] || { echo "FAIL: jModelTest.jar missing"; exit 1; }

# extract 18S_insects2.nex (72 sequences, DNA) to a writable work dir
mkdir -p "$BUILD_DIR/example"
"$JAR_TOOL" xf "$JAR" example-data/18S_insects2.nex
mv example-data/18S_insects2.nex "$BUILD_DIR/example/18S_insects2.nex" 2>/dev/null || true
INPUT="$BUILD_DIR/example/18S_insects2.nex"
[ -f "$INPUT" ] || { echo "FAIL: example alignment not extracted"; exit 1; }

echo "==> [2/3] -help (JVM + jar + classpath smoke)"
"$JMT" -help > "$BUILD_DIR/help.out" 2>&1 || true
grep -qiE "usage|jmodeltest|ModelTest" "$BUILD_DIR/help.out" \
  && { echo "OK: -help printed usage"; } \
  || { echo "FAIL: -help did not print usage"; cat "$BUILD_DIR/help.out"; exit 1; }

echo "==> [3/3] -d <nexus> -getPhylip (real headless conversion)"
"$JMT" -d "$INPUT" -getPhylip > "$BUILD_DIR/getphylip.out" 2>&1
# should write <input>.phy next to the input
grep -qiE "OK|Result written" "$BUILD_DIR/getphylip.out" \
  && { echo "OK: conversion reported success"; } \
  || { echo "FAIL: conversion did not report success"; cat "$BUILD_DIR/getphylip.out"; exit 1; }
[ -f "$INPUT.phy" ] && [ -s "$INPUT.phy" ] \
  && { echo "OK: wrote $(wc -l < "$INPUT.phy")-line phylip output"; } \
  || { echo "FAIL: phylip output missing/empty"; exit 1; }

echo "==> jmodeltest consumer test PASSED"