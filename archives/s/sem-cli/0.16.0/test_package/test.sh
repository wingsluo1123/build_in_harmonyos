#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for sem CLI executable
set -eu

echo "[test] sem --version"
sem --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    sem --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ sem failed both --version and --help"
        exit 1
    }
}
