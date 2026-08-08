#!/bin/sh
# Test script for rsyslog test_package
# R34: Execute the actual binary to verify it works
# Runs rsyslogd -v to check version output

RSYSLOGD="$1"
if [ -z "$RSYSLOGD" ]; then
    echo "Usage: test_rsyslog.sh <path-to-rsyslogd>"
    exit 1
fi

output=$("$RSYSLOGD" -v 2>&1)
if echo "$output" | grep -q "rsyslogd"; then
    echo "test rsyslog 8.2404.0: OK"
    echo "Version output: $output"
    exit 0
else
    echo "test rsyslog 8.2404.0: FAIL"
    echo "Expected 'rsyslogd' in output, got: $output"
    exit 1
fi
