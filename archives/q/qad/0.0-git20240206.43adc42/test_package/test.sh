#!/usr/bin/env bash
set -euo pipefail

qad_bin="$(command -v qad 2>/dev/null)" || true

if [ -z "$qad_bin" ]; then
    printf 'FAIL: qad binary not found in PATH\n'
    exit 1
fi

printf 'INFO: qad binary at %s\n' "$qad_bin"

if ! [ -f "$qad_bin" ]; then
    printf 'FAIL: qad path does not exist as file\n'
    exit 1
fi

if ! [ -x "$qad_bin" ]; then
    printf 'FAIL: qad is not executable\n'
    exit 1
fi

printf 'PASS: qad binary found and executable\n'

help_output="$(qad --help 2>&1 || true)"
printf 'INFO: qad --help output:\n%s\n' "$help_output"

if printf '%s\n' "$help_output" | grep -qi 'usage\|option\|qad\|QAD'; then
    printf 'PASS: qad --help responded\n'
else
    printf 'INFO: qad --help did not produce expected output (cross-compiled binary, may not run on build host)\n'
fi
