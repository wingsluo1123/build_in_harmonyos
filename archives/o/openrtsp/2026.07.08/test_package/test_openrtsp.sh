#!/system/bin/sh
# test_openrtsp.sh — verify openRTSP binary runs and prints usage text
# openRTSP without arguments prints usage to stderr and exits non-zero.
# This test checks that "Usage:" appears in the output.
BINARY="${1:-openRTSP}"
OUTPUT=$("$BINARY" 2>&1)
RC=$?
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "Usage:"; then
    echo "test_openrtsp PASS: openRTSP produced usage text (exit $RC)"
    exit 0
else
    echo "test_openrtsp FAIL: openRTSP did not produce usage text (exit $RC)"
    exit 1
fi
