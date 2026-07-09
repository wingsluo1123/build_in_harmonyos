#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for tmux executable
set -eu

echo "[test] tmux -V"
tmux -V && echo "OK --version OK" || {
    echo "[test] --version failed, trying --help..."
    tmux --help > /dev/null 2>&1 && echo "OK --help OK" || {
        echo "FAIL tmux failed both -V and --help"
        exit 1
    }
}
