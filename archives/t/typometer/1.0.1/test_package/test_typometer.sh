#!/bin/bash
# test_typometer.sh — consumer smoke test for the packaged typometer JAR.
#
# Compiles and runs TestTypometer.java against the packaged uber-JAR. The test
# is self-contained (no external fixtures): it loads the packaged classes,
# calls real public APIs (SummaryStatistics / Series / ChartData /
# FrequencyDistribution) and checks the HarmonyOS platform-detection
# adaptation.
#
# Usage: test_typometer.sh <package_folder> [target_os]
set -euo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"
TARGET_OS="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"

# On OHOS, require the HarmonyOS-specific platform-detection assertions.
JAVA_EXTRA=""
if [ "$TARGET_OS" = "OHOS" ]; then
    JAVA_EXTRA="--require-harmonyos"
fi

# ── resolve JAVA_HOME (env first, then common install locations) ──
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
    for candidate in \
        "$HOME/bishengjdk17" \
        "$HOME/usr/local/bishengjdk17" \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -x "$candidate/bin/java" ]; then
            JAVA_HOME="$candidate"
            break
        fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
    echo "ERROR: JAVA_HOME not set and no JDK found in common locations." >&2
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

JAR_PATH="$PKG_DIR/libexec/typometer-1.0.1.jar"
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: packaged JAR not found at $JAR_PATH" >&2
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

# /tmp may be read-only on OHOS; fall back to $HOME.
WORK="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"
trap 'rm -rf "$WORK"' EXIT

echo "=== compiling consumer test ==="
javac -cp "$JAR_PATH" "$HERE/TestTypometer.java" -d "$WORK"

echo "=== running consumer test (target_os=${TARGET_OS:-unknown}) ==="
set +e
OUT="$(java -cp "$JAR_PATH:$WORK" TestTypometer $JAVA_EXTRA 2>&1)"
RC=$?
set -e
echo "$OUT"

PASSED_N="$(printf '%s\n' "$OUT" | sed -n 's/.*TEST SUMMARY: \([0-9]*\) passed.*/\1/p')"
FAILED_N="$(printf '%s\n' "$OUT" | sed -n 's/.*TEST SUMMARY: [0-9]* passed, \([0-9]*\) failed.*/\1/p')"
PASSED_N="${PASSED_N:-0}"
FAILED_N="${FAILED_N:-1}"
TOTAL=$((PASSED_N + FAILED_N))

if [ "$RC" -ne 0 ] || [ "$FAILED_N" -ne 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\": true, \"passed\": false, \"discovered\": $TOTAL, \"passedCount\": $PASSED_N, \"failedCount\": $FAILED_N, \"target_os\": \"${TARGET_OS:-unknown}\"}"
    echo "ERROR: consumer test failed (rc=$RC, $FAILED_N failed assertions)" >&2
    exit 1
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\": true, \"passed\": true, \"discovered\": $TOTAL, \"passedCount\": $PASSED_N, \"failedCount\": 0, \"target_os\": \"${TARGET_OS:-unknown}\"}"
echo "=== consumer test passed ($PASSED_N/$TOTAL) ==="
