#!/usr/bin/env bash
set -eu

pkg="${1:?package path required}"
emqx="$pkg/bin/emqx"

test -x "$emqx"
test -d "$pkg/releases/5.8.8"
test -d "$pkg/etc"
test -d "$pkg/lib"

EMQX_LOG_DIR="${TMPDIR:-/tmp}/emqx-test-log" \
EMQX_NODE__DATA_DIR="${TMPDIR:-/tmp}/emqx-test-data" \
  "$emqx" help >/dev/null
