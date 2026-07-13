#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gofumpt executable
set -eu

echo "[test] gofumpt -version"
gofumpt -version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    gofumpt --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ gofumpt failed both --version and --help"
        exit 1
    }
}

echo "[test] gofumpt -h (help text)"
gofumpt -h | head -5

echo "[test] All smoke tests passed ✅"
