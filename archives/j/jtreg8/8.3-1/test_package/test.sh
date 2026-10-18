#!/usr/bin/env bash
# test.sh — jtreg8 consumer test (R34)
#
# Runs the packaged jtreg binary against a real mini JDK test suite
# (one passing test + one intentionally failing test as negative control)
# and verifies the produced reports. Works on HarmonyOS PC and on CI.
#
# The Conan CI L1e destructive check removes bin/ and lib/ from the package
# before re-running this test; every assertion below executes the packaged
# jtreg, so the test genuinely depends on the package.

set -euo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-}}"
if [ -z "$PKG_DIR" ]; then
    echo "ERROR: package folder not provided" >&2
    exit 1
fi

# Resolve JAVA_HOME: env first, then common cmd-pkgs / distro locations.
# (build() auto-installs bishengjdk 17 via cmd-pkgs when the host lacks a JDK.)
if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then
    for candidate in \
        "$HOME/bishengjdk17" \
        "$HOME/usr/local/bishengjdk17" \
        /storage/Users/currentUser/bishengjdk17 \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -f "$candidate/bin/java" ]; then
            JAVA_HOME="$candidate"
            break
        fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then
    echo "ERROR: JAVA_HOME not set and no JDK found in common locations." >&2
    echo "Set JAVA_HOME to a JDK 17+ installation path." >&2
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

JTREG="$PKG_DIR/bin/jtreg"
JTREG_JAR="$PKG_DIR/lib/jtreg.jar"
JTDIFF="$PKG_DIR/bin/jtdiff"
# /tmp is read-only on the OHOS sandbox (EROFS); fall back to $HOME.
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"
trap 'rm -rf "$TMP_DIR"' EXIT

ASSERT=0
ok() { ASSERT=$((ASSERT + 1)); echo "OK: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

echo "=== jtreg8 consumer test ==="

# 1-3: packaged artifacts
[ -f "$JTREG" ] && ok "bin/jtreg present" || fail "bin/jtreg missing"
[ -f "$JTDIFF" ] && ok "bin/jtdiff present" || fail "bin/jtdiff missing"
[ -f "$JTREG_JAR" ] && ok "lib/jtreg.jar present" || fail "lib/jtreg.jar missing"

# 4-5: executable smoke — version banner and runtime JDK detection
VERSION_OUT="$(sh "$JTREG" -version 2>&1)"
echo "$VERSION_OUT" | grep -q 'jtreg 8.3+1' \
    && ok "bin/jtreg -version reports jtreg 8.3+1" \
    || fail "unexpected jtreg version output: $VERSION_OUT"
echo "$VERSION_OUT" | grep -q 'Running on platform version' \
    && ok "bin/jtreg reports the runtime JDK" \
    || fail "jtreg did not report the runtime JDK"

# 6: companion tool executes
if sh "$JTDIFF" -version >/dev/null 2>&1 || sh "$JTDIFF" -help >/dev/null 2>&1; then
    ok "bin/jtdiff executes"
else
    fail "bin/jtdiff did not execute"
fi

# Build a mini JDK test suite: 1 passing test + 1 intentionally failing test
SUITE="$TMP_DIR/suite"
mkdir -p "$SUITE"
: > "$SUITE/TEST.ROOT"

cat > "$SUITE/Passing.java" <<'EOF'
/*
 * @test
 * @summary the packaged jtreg must compile and run a JDK test
 * @run main Passing
 */
public class Passing {
    public static void main(String[] args) {
        System.out.println("JTREG8-SMOKE-OK");
    }
}
EOF

cat > "$SUITE/Failing.java" <<'EOF'
/*
 * @test
 * @summary negative control: an intentional failure must be reported as failed
 * @run main Failing
 */
public class Failing {
    public static void main(String[] args) {
        throw new RuntimeException("jtreg8-intentional-failure");
    }
}
EOF

WORK="$TMP_DIR/work"
REPORT="$TMP_DIR/report"
set +e
RUN_OUT="$(sh "$JTREG" -jdk:"$JAVA_HOME" -w "$WORK" -r "$REPORT" "$SUITE" 2>&1)"
RUN_RC=$?
set -e

# 7: exit code reflects the failing test
if [ "$RUN_RC" -ne 0 ]; then
    ok "jtreg exit code reflects the failing test (rc=$RUN_RC)"
else
    fail "jtreg returned 0 although one test was designed to fail"
fi

# 8: aggregate result line
if echo "$RUN_OUT" | grep -q 'Test results: passed: 1; failed: 1'; then
    ok "aggregate result 'passed: 1; failed: 1' reported"
else
    fail "unexpected aggregate result: $(echo "$RUN_OUT" | tail -3)"
fi

# 9-10: per-test summary
grep -q 'Passing.java  Passed' "$REPORT/text/summary.txt" \
    && ok "summary reports Passing.java Passed" \
    || fail "summary missing Passing.java Passed"
grep -q 'Failing.java  Failed' "$REPORT/text/summary.txt" \
    && ok "summary reports Failing.java Failed" \
    || fail "summary missing Failing.java Failed"

# 11: the passing test really executed (its stdout is in the .jtr)
grep -q 'JTREG8-SMOKE-OK' "$WORK/Passing.jtr" \
    && ok "Passing.jtr contains the test's stdout" \
    || fail "Passing.jtr does not contain the test output"

# 12: the failure reason is visible in the .jtr
grep -q 'jtreg8-intentional-failure' "$WORK/Failing.jtr" \
    && ok "Failing.jtr contains the intentional exception" \
    || fail "Failing.jtr does not contain the failure reason"

echo "=== All tests passed ==="
echo "PASS: jtreg8 consumer test (${ASSERT} assertions, 1 jtreg suite run)"
