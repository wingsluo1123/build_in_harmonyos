#!/data/service/hnp/bin/bash
# test_package/test.sh - pdftk 3.3.3 consumer verification (R34 substantive)
# 1) Structure: packaged pdftk home (bin/pdftk.jar + bin/pdftk + lib/*.jar)
# 2) Real run of the packaged CLI: pdftk --version must report 3.3.3
# 3) Compile and run the Java consumer (TestPdftk.java): iText PDF creation
#    + pdftk cat round-trip + dump_data, 9 real assertions
#
# Counts: 3 shell checks + 9 consumer assertions = 12 test cases.
# The HMBS_TEST_PACKAGE_RESULT marker carries passedCount counted from the
# actual OK lines in this run's logs (single deterministic source).

set -u

SHELL_TOTAL=3
JAVA_EXPECTED=9
DISCOVERED=12

shell_passed=0

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"

# Resolve JAVA_HOME: env first, then common JDK locations
# (HNP bundled java may fail to start in some environments,
# so prefer ~/bishengjdk17 installed via cmd-pkgs)
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    for candidate in \
        "$HOME/bishengjdk17" \
        /storage/Users/currentUser/bishengjdk17 \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -d "$candidate" ]; then
            JAVA_HOME="$candidate"
            break
        fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/java" ]; then
    echo "FAIL: JAVA_HOME not set and no JDK found in common locations." >&2
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh\",\"discovered\":${DISCOVERED},\"passedCount\":0}"
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

# /tmp may be read-only (EROFS) in the OHOS sandbox; fall back to $HOME
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"
trap 'rm -rf "$TMP_DIR"' EXIT

PDK_HOME="$PKG_DIR/libexec/pdftk"

echo "=== pdftk 3.3.3 consumer verification ==="

# S1: main jar present
JAR_MAIN="$PDK_HOME/bin/pdftk.jar"
if [ ! -f "$JAR_MAIN" ]; then
    echo "FAIL: pdftk.jar not found at $JAR_MAIN"
else
    echo "OK: pdftk.jar found"
    shell_passed=$((shell_passed + 1))
fi

# S2: runtime dependency jars present (ivy build conf: bcprov + commons-lang3)
LIB_COUNT=0
for j in "$PDK_HOME"/lib/*.jar; do
    [ -f "$j" ] && LIB_COUNT=$((LIB_COUNT + 1))
done
if [ -f "$PDK_HOME/lib/bcprov-jdk18on-1.71.jar" ] && [ -f "$PDK_HOME/lib/commons-lang3-3.12.0.jar" ]; then
    echo "OK: runtime jars present (lib/*.jar = $LIB_COUNT)"
    shell_passed=$((shell_passed + 1))
else
    echo "FAIL: runtime jars incomplete (lib/*.jar = $LIB_COUNT)"
fi

# S3: real run of the packaged CLI entry
VERSION_OUT="$(sh "$PDK_HOME/bin/pdftk" --version 2>&1)" || {
    echo "FAIL: pdftk --version failed"
    echo "$VERSION_OUT"
}
if printf '%s\n' "${VERSION_OUT:-}" | grep -q "3\.3\.3"; then
    echo "$VERSION_OUT" | head -n 1
    echo "OK: pdftk --version reports 3.3.3"
    shell_passed=$((shell_passed + 1))
else
    echo "FAIL: pdftk did not report 3.3.3"
    printf '%s\n' "${VERSION_OUT:-}"
fi

# Consumer program: compile against the packaged jars and run it.
CP="$JAR_MAIN"
for j in "$PDK_HOME"/lib/*.jar; do
    [ -f "$j" ] && CP="$CP:$j"
done
TEST_SRC="$(dirname "$0")/TestPdftk.java"

if ! javac -encoding UTF-8 -cp "$CP" "$TEST_SRC" -d "$TMP_DIR" 2>&1; then
    echo "FAIL: javac compilation failed"
    CLOG=""
else
    echo "OK: TestPdftk.java compiled successfully (build step, not counted)"
    CLOG="$TMP_DIR/consumer.log"
    if ! java -cp "$CP:$TMP_DIR" TestPdftk "$TMP_DIR" >"$CLOG" 2>&1; then
        echo "FAIL: Java consumer execution failed"
        cat "$CLOG"
        CLOG=""
    fi
fi

java_ok=0
if [ -n "${CLOG:-}" ] && grep -q "^PASS:" "$CLOG"; then
    cat "$CLOG"
    java_ok=$(grep -c '^OK\[' "$CLOG")
fi

passed=$((shell_passed + java_ok))
if [ "$shell_passed" -eq "$SHELL_TOTAL" ] && [ "$java_ok" -eq "$JAVA_EXPECTED" ]; then
    echo "=== All tests passed ==="
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test.sh\",\"discovered\":${DISCOVERED},\"passedCount\":${passed}}"
    exit 0
else
    echo "FAIL: ${passed}/${DISCOVERED} checks passed (shell ${shell_passed}/${SHELL_TOTAL}, consumer ${java_ok}/${JAVA_EXPECTED})"
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh\",\"discovered\":${DISCOVERED},\"passedCount\":${passed}}"
    exit 1
fi
