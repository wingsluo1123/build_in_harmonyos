#!/usr/bin/env bash
set -euo pipefail

# Find arduino-cli binary in PATH (set up by conanrun environment)
arduino_cli_bin="$(command -v arduino-cli 2>/dev/null || true)"

if [ -z "$arduino_cli_bin" ]; then
    echo "arduino-cli binary not found in PATH" >&2
    exit 1
fi

if [ ! -f "$arduino_cli_bin" ]; then
    echo "arduino-cli binary not found: $arduino_cli_bin" >&2
    exit 1
fi

# Test 1: --help should succeed and print usage
"$arduino_cli_bin" --help >/dev/null

# Test 2: version command should contain version string
version_output="$("$arduino_cli_bin" version)"

# The version output should contain "arduino-cli" and the version "1.5.0"
printf '%s\n' "$version_output" | grep -F "arduino-cli" >/dev/null
printf '%s\n' "$version_output" | grep -F "1.5.0" >/dev/null

echo "All tests passed."
