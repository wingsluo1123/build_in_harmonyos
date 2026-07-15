#!/bin/bash
set -euo pipefail

if command -v hexedit >/dev/null 2>&1; then
    echo "hexedit found in PATH"
    hexedit --help
    echo "hexedit --help: OK"
else
    echo "FAIL: hexedit not found"
    exit 1
fi