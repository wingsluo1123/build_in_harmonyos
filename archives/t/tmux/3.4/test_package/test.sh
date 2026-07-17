#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for tmux binary
set -eu

echo "[test] tmux -V"
tmux -V && echo "✅ tmux -V OK" || {
    echo "❌ tmux -V failed"
    exit 1
}
