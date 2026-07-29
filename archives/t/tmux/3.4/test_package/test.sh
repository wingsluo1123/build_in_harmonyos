#!/usr/bin/env bash
# test_package/test.sh - smoke test for the packaged tmux executable
set -euo pipefail

echo "[test] tmux -V"
actual="$(tmux -V)"
test "$actual" = "tmux 3.4"
echo "[ok] tmux version matched: $actual"
