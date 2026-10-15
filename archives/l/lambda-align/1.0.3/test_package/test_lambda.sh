#!/bin/sh
# test_package for lambda-align 1.0.3 (CLI tools)
# R34: actually execute the packaged binaries and validate their output.
set -e

echo "== lambda --version =="
lambda_out="$(lambda --version 2>&1)"
echo "$lambda_out"
# Upstream hardcodes 1.0.2 in src/CMakeLists.txt (known upstream issue);
# accept either version but require the banner and the SeqAn line.
echo "$lambda_out" | grep -q "lambda version:"
echo "$lambda_out" | grep -q "SeqAn version: 2.3.2"

echo "== lambda_indexer --version =="
indexer_out="$(lambda_indexer --version 2>&1)"
echo "$indexer_out"
echo "$indexer_out" | grep -q -i "version"

echo "lambda-align 1.0.3 smoke test: OK"
