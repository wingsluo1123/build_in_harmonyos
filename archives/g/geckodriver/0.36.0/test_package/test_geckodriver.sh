#!/usr/bin/zsh
# test_geckodriver.sh — L1 test source file for geckodriver
# Runs geckodriver --version to verify the binary is functional
# Standalone test utility (L0c source file requirement)

set -euo pipefail

GECKODRIVER="${GECKODRIVER:-geckodriver}"
echo "Testing: $GECKODRIVER --version"
"$GECKODRIVER" --version
echo "PASS: geckodriver binary is functional"
