#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dex2jar 2.4
# Verifies d2j-dex2jar script exists and executes; fails loudly if not.
set -eu -o pipefail

echo "=== dex2jar smoke test ==="

# Locate the d2j-dex2jar script in the package
SCRIPT="d2j-dex2jar"
if [ -f "${DEX2JAR_HOME}/bin/${SCRIPT}" ]; then
    SCRIPT_PATH="${DEX2JAR_HOME}/bin/${SCRIPT}"
elif [ -f "${DEX2JAR_HOME}/bin/${SCRIPT}.bat" ]; then
    SCRIPT_PATH="${DEX2JAR_HOME}/bin/${SCRIPT}.bat"
else
    echo "ERROR: ${SCRIPT} not found under ${DEX2JAR_HOME}/bin/"
    exit 1
fi

echo "Testing: ${SCRIPT_PATH} --help"
if command -v java > /dev/null 2>&1; then
    "${SCRIPT_PATH}" --help > /dev/null 2>&1 || {
        echo "ERROR: ${SCRIPT_PATH} --help failed (exit $?)"
        exit 1
    }
    echo "=== dex2jar smoke test PASSED ==="
else
    echo "ERROR: Java not found in PATH — cannot verify binary execution."
    ls -la "${SCRIPT_PATH}"
    exit 1
fi
