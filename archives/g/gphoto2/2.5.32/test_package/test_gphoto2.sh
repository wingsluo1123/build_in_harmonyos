#!/bin/sh
# Test script for gphoto2 — verifies the binary is installed and functional
# R34: test must exercise the actual binary
gphoto2 --version > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "gphoto2 test PASSED: binary is functional"
    exit 0
else
    echo "gphoto2 test FAILED: binary not working"
    exit 1
fi
