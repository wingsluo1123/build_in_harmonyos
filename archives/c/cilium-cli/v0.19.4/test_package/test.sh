#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cilium executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] cilium version"
cilium version && echo "✅ version OK" || {
    echo "[test] version failed, trying --help..."
    cilium --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ cilium failed both version and --help"
        exit 1
    }
}
