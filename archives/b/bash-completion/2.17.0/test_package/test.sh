#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bash-completion
set -eu

echo "[test] bash-completion --version"
bash-completion --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bash-completion --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bash-completion failed"
        exit 1
    }
}
