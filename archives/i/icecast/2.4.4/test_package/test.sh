#!/usr/bin/env bash
set -euo pipefail
"$1" --version 2>&1 | grep -i "icecast"
