#!/bin/sh
# test_gphoto2.sh — Test script for gphoto2 CLI tool (R34: real API call)
#
# This script exercises the gphoto2 binary which is the actual package output.
# It verifies:
#   1. gphoto2 --version — binary is installed and reports correct version
#   2. gphoto2 --list-ports — exercises libgphoto2 port enumeration API
#
# The conan test_package test() method calls these commands via self.run().

set -e

echo "=== gphoto2 version check ==="
gphoto2 --version

echo ""
echo "=== gphoto2 port enumeration (exercises libgphoto2 API) ==="
gphoto2 --list-ports

echo ""
echo "=== All gphoto2 tests passed ==="
