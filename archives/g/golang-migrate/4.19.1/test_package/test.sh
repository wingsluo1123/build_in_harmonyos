#!/usr/bin/env bash
# Consumer smoke test for golang-migrate 4.19.1.
# Asserts: (1) `migrate -help` exits 0; (2-5) stable driver keywords present.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-migrate>" >&2
    exit 2
fi

migrate_bin="$1"

if [ ! -f "$migrate_bin" ]; then
    echo "migrate binary not found: $migrate_bin" >&2
    exit 1
fi

# Capture `migrate -help` output. migrate prints help to stdout on -help and exits 0.
help_output="$("$migrate_bin" -help 2>&1)" || {
    echo "migrate -help exited non-zero" >&2
    exit 1
}

# Assertion 2: postgres driver present
printf '%s\n' "$help_output" | grep -F "postgres" >/dev/null
# Assertion 3: mysql driver present
printf '%s\n' "$help_output" | grep -F "mysql" >/dev/null
# Assertion 4: sqlite driver present
printf '%s\n' "$help_output" | grep -F "sqlite" >/dev/null
# Assertion 5: file source present
printf '%s\n' "$help_output" | grep -F "file" >/dev/null

echo "golang-migrate consumer smoke test: PASS"
