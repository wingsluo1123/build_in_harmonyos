#!/bin/bash
set -euo pipefail
# test.sh — nxp-mfgtools (uuu) L1 test
# Runs `uuu -h` to verify the binary links and executes correctly.
# The conanrun environment sets up PATH and LD_LIBRARY_PATH so that
# the uuu binary and its shared library deps are found.

echo "[step] Running uuu -h..."
uuu -h 2>&1 | head -5
echo "        [ok] uuu binary executed successfully"
