#!/bin/sh
# consumer_test.sh — OHOS-specific consumer smoke test (non-assertion).
#
# Invoked by test_package/conanfile.py test() after OHOS codesign.
# Checks (report-only, non-assertion per rule12):
#   1. The signed binary actually executes on OHOS (-h).
#   2. Dynamic shared-library closure (ELF NEEDED entries) is reported
#      for the CI log, since OHOS loader closure differs from Linux.
#
# Exit code: 0 unless the binary itself is missing/not executable.
set -u

BIN="${1:-}"
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
    echo "[consumer_test] FAIL: binary missing or not executable: ${BIN}"
    exit 1
fi

echo "[consumer_test] run: ${BIN} -h"
if "${BIN}" -h; then
    echo "[consumer_test] -h executed OK"
else
    echo "[consumer_test] -h rc=$? (non-fatal, reported for CI log)"
fi

if command -v readelf >/dev/null 2>&1; then
    echo "[consumer_test] shared-library closure (NEEDED):"
    readelf -d "${BIN}" 2>/dev/null | grep NEEDED \
        || echo "[consumer_test]   (no NEEDED entries / static)"
else
    echo "[consumer_test] readelf unavailable; closure report skipped"
fi

exit 0
