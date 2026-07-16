#!/bin/sh
# test_docker.sh — L0c test source file for docker CLI
# Verifies that the docker binary reports its version correctly
#
# This file satisfies CI gate L0c (test source files requirement).
# The actual test logic is in conanfile.py's test() method which
# copies the binary to a temp dir, signs it, and runs --version.

DOCKER_BIN="${1:-docker}"
output=$("$DOCKER_BIN" --version 2>&1)
echo "$output"
echo "$output" | grep -q "Docker version 29.5.3"
