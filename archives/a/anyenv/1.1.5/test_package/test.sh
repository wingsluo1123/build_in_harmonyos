#!/usr/bin/env bash
set -euo pipefail

anyenv -v
anyenv commands | grep '^version$'
anyenv help version | grep 'Usage: anyenv version'
anyenv root | grep -Fx "$ANYENV_ROOT"
