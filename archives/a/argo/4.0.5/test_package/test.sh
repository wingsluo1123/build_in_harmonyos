#!/usr/bin/env bash
# Consumer smoke test for argo 4.0.5.
# Asserts: (1) `argo version` exits 0; (2) version string contains v4.0.5;
#          (3) `argo help` exits 0; (4) help output lists subcommands.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-argo>" >&2
    exit 2
fi

argo_bin="$1"

if [ ! -f "$argo_bin" ]; then
    echo "argo binary not found: $argo_bin" >&2
    exit 1
fi

# Assertion 1: `argo version` exits 0
version_output="$("$argo_bin" version 2>&1)" || {
    echo "argo version exited non-zero" >&2
    exit 1
}

# Assertion 2: version output contains v4.0.5
printf '%s\n' "$version_output" | grep -F "v4.0.5" >/dev/null

# Assertion 3: `argo help` exits 0
help_output="$("$argo_bin" help 2>&1)" || {
    echo "argo help exited non-zero" >&2
    exit 1
}

# Assertion 4: help output lists common subcommands
printf '%s\n' "$help_output" | grep -F "submit" >/dev/null
printf '%s\n' "$help_output" | grep -F "list" >/dev/null
printf '%s\n' "$help_output" | grep -F "lint" >/dev/null

echo "argo consumer smoke test: PASS"
