#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for mp3cat executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] mp3cat --version"
mp3cat --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    mp3cat --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ mp3cat failed both --version and --help"
        exit 1
    }
}
