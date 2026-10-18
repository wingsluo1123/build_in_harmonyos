#!/data/service/hnp/bin/bash
# test_package/test.sh — OHOS consumer smoke test for the vdr executable.
#
# Usage: test.sh <absolute-path-to-vdr>
#
# The binary is a DVR daemon; with no DVB adapter on the device the only
# consumer-verifiable behaviour is the pre-device command line handling plus
# the documented "video directory not accessible" failure path.
set -euo pipefail

VDR="${1:?usage: test.sh <absolute-path-to-vdr>}"

if [ ! -x "$VDR" ]; then
    echo "FAIL: $VDR is not executable"
    exit 1
fi
echo "[test] executable: $VDR"

echo "[test] 1/3 vdr --version exits 0 and reports 2.6.9"
VER_OUT="$("$VDR" --version < /dev/null)"
echo "      output: $VER_OUT"
echo "$VER_OUT" | grep -q "vdr (2.6.9/2.6.9)" || {
    echo "FAIL: --version did not report 'vdr (2.6.9/2.6.9)'"
    exit 1
}

echo "[test] 2/3 vdr --help exits 0 and lists the documented options"
HELP_OUT="$("$VDR" --help < /dev/null)"
if ! echo "$HELP_OUT" | grep -q -- "--video=DIR"; then
    echo "FAIL: --help did not list --video=DIR"
    exit 1
fi
if ! echo "$HELP_OUT" | grep -q -- "--config=DIR"; then
    echo "FAIL: --help did not list --config=DIR"
    exit 1
fi
echo "      help lines: $(echo "$HELP_OUT" | wc -l)"

echo "[test] 3/3 missing video directory is rejected with a diagnostic"
set +e
FAIL_OUT="$("$VDR" --video=/nonexistent-vdr-video-dir --config=/nonexistent-vdr-conf-dir --user=root < /dev/null 2>&1)"
FAIL_RC=$?
set -e
echo "      rc=$FAIL_RC output: $FAIL_OUT"
if [ "$FAIL_RC" -eq 0 ]; then
    echo "FAIL: vdr accepted a nonexistent video directory"
    exit 1
fi
if ! echo "$FAIL_OUT" | grep -q "can't access video directory"; then
    echo "FAIL: expected the 'can't access video directory' diagnostic"
    exit 1
fi

echo "[test] OK: 3/3 consumer smoke assertions passed"
