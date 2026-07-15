#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for picocom executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] picocom --help"
picocom --help > /dev/null 2>&1 && echo "✅ --help OK" || {
    echo "❌ picocom --help failed"
    exit 1
}

echo "[test] picocom version string"
picocom --help 2>&1 | head -1 | grep -q "picocom" && echo "✅ version string OK" || {
    echo "❌ picocom version string not found"
    exit 1
}
