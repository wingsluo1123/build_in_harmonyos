#!/usr/bin/env bash
# test.sh — jama 1.0.3 consumer API + HarmonyOS feasibility test.
#
# Compiles TestJama.java against the packaged jama-1.0.3.jar and runs it with
# the same JVM a consumer on HarmonyOS PC would use.  Satisfies R34 (the test
# calls the real library API) and provides the HarmonyOS consumer cases
# (OHOS-1..OHOS-4 inside TestJama.java).
#
# Usage: bash test.sh <jama-1.0.3.jar> [java_home]
#
# Emits HMBS_TEST_PACKAGE_RESULT=<json> with the real check counts parsed from
# the program output (never hard coded).
set -euo pipefail

JAR_PATH="${1:-${JAMA_JAR:-}}"
JAVA_HOME_ARG="${2:-}"

# HarmonyOS: /tmp is read-only.  Pick the first writable scratch directory —
# injected TMPDIR/TMP/TEMP, then a user cache dir; the archive tree is used
# only as an absolute last resort (it must stay clean for the PR).
_pick_tmp() {
    for candidate in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}" \
                     "${HOME:-}/.cache/jama-test" "${HOME:-}/tmp"; do
        [ -n "$candidate" ] || continue
        if mkdir -p "$candidate" 2>/dev/null && [ -w "$candidate" ]; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    return 1
}
WORK_TMP="$(_pick_tmp || true)"
if [ -z "$WORK_TMP" ]; then
    WORK_TMP="$(pwd)/.jama-tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null || WORK_TMP="$(dirname "$0")/.jama-tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null
fi
export TMPDIR="$WORK_TMP" TMP="$WORK_TMP" TEMP="$WORK_TMP"

# ── locate a JDK (argument > environment > well-known OHOS installs) ──────
if [ -n "$JAVA_HOME_ARG" ] && [ -x "$JAVA_HOME_ARG/bin/javac" ]; then
    JAVA_HOME="$JAVA_HOME_ARG"
elif [ -n "${JAVA_HOME:-}" ] && [ -x "${JAVA_HOME}/bin/javac" ]; then
    :
else
    for candidate in \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
        /storage/Users/currentUser/bishengjdk17 \
        ~/bishengjdk17 \
        ~/usr/local/bishengjdk17 \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -x "$candidate/bin/javac" ]; then
            JAVA_HOME="$candidate"
            break
        fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/javac" ]; then
    echo "ERROR: no JDK found (set JAVA_HOME to a JDK 17+ installation)." >&2
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,"command":"bash test.sh","discovered":0,"passedCount":0,"reason":"no JDK"}\n'
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

TEST_SRC="$(dirname "$0")/TestJama.java"
TMP_DIR="$(mktemp -d "${WORK_TMP}/jama.XXXXXX" 2>/dev/null || mktemp -d)"
# `|| true`: the cleanup must never change the script's exit status (on
# HarmonyOS / some sandboxes `rm` itself can be unusable).
trap 'rm -rf "$TMP_DIR" 2>/dev/null || true' EXIT

echo "=== jama 1.0.3 consumer test (HarmonyOS PC) ==="
echo "JDK: $JAVA_HOME"
echo "JAR: $JAR_PATH"

if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: jama JAR not found at '$JAR_PATH'" >&2
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,"command":"bash test.sh","discovered":0,"passedCount":0,"reason":"jar missing"}\n'
    exit 1
fi

# Exported so TestJama can prove the JAR is consumed through the Conan package
# layout (OHOS-2) and audit its contents (OHOS-4).
export JAMA_JAR="$JAR_PATH"

echo "--- compiling TestJama.java against the packaged JAR ---"
if ! javac -cp "$JAR_PATH" -d "$TMP_DIR" "$TEST_SRC"; then
    echo "ERROR: javac compilation against the packaged JAR failed" >&2
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,"command":"bash test.sh","discovered":0,"passedCount":0,"reason":"javac failed"}\n'
    exit 1
fi

# The class runs in a writable working directory (OHOS-3 needs one): the
# packaged library is exercised against the real HarmonyOS filesystem.
echo "--- running TestJama (cwd=$TMP_DIR) ---"
set +e
output="$(cd "$TMP_DIR" && java -cp "$JAR_PATH:$TMP_DIR" TestJama 2>&1)"
rc=$?
set -e
echo "$output"

passed_n="$(printf '%s\n' "$output" | sed -n 's/.*RESULT CHECKS: passed=\([0-9]*\).*/\1/p' | tail -1)"
failed_n="$(printf '%s\n' "$output" | sed -n 's/.*RESULT CHECKS: passed=[0-9]* failed=\([0-9]*\).*/\1/p' | tail -1)"
total_n="$(printf '%s\n' "$output" | sed -n 's/.*RESULT CHECKS: .* total=\([0-9]*\).*/\1/p' | tail -1)"
passed_n="${passed_n:-0}"
failed_n="${failed_n:-0}"
total_n="${total_n:-0}"

if [ "$rc" -eq 0 ] && [ "$failed_n" -eq 0 ] && [ "$total_n" -gt 0 ] \
   && printf '%s\n' "$output" | grep -q "ALL JAMA CHECKS PASSED"; then
    echo "=== All jama consumer checks passed (passed=$passed_n total=$total_n) ==="
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
        "$total_n" "$passed_n"
    exit 0
fi

echo "ERROR: jama consumer checks failed (rc=$rc passed=$passed_n failed=$failed_n total=$total_n)" >&2
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
    "$total_n" "$passed_n"
exit 1
