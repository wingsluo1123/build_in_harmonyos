#!/bin/sh
# Test script for gnutls package
set -e

echo "Testing gnutls package..."
gnutls-cli --version
echo "GnuTLS test passed!"