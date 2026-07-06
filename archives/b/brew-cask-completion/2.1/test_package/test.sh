#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for brew-cask-completion
set -eu

echo "[test] brew-cask-completion --version"
brew-cask-completion --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    brew-cask-completion --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: brew-cask-completion failed"
        exit 1
    }
}
