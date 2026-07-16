#!/bin/bash
# test.sh — wireguard-tools smoke test
# Actual test execution is done by test_package/conanfile.py's test() method
# via Conan's test framework. This script documents the test approach.
set -euo pipefail

# Test 1: --help shows usage (verifies binary is functional)
wg --help

# Test 2: genkey produces a valid base64 key (tests curve25519 crypto)
KEY=$(wg genkey)
echo "Generated key: $KEY"

# Test 3: pubkey derives public key from private key
echo "$KEY" | wg pubkey

echo "All tests passed"
