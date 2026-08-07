#!/usr/bin/env sh
set -eu

: "${PERL:=perl}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$PERL" "$SCRIPT_DIR/test_mailtools.pl"
