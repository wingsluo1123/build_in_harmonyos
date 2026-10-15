#!/bin/sh
# Consumer test driver for the installed zenmap package.
#
# Runs under the conanrun environment: PYTHONPATH already contains the zenmap
# package payload and PATH the nmap/7.99 run dependency.  No shell-rc or
# `cd` dependency — everything is resolved from the test_package folder.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

echo "[zenmap test_package] interpreter: $(command -v "$PYTHON")"
echo "[zenmap test_package] nmap binary : ${ZENMAP_TEST_NMAP:-<unset>}"

"$PYTHON" "$HERE/test_core.py"
