#!/bin/sh
# test_package/test.sh — smoke test for the cdo executable.
set -eu

CDO_BIN="${CDO_BIN:-cdo}"

echo "[test] $CDO_BIN --version"
"$CDO_BIN" --version >/dev/null

echo "[test] $CDO_BIN --help"
"$CDO_BIN" --help >/dev/null

echo "[ok] cdo executable responded to --version and --help"
