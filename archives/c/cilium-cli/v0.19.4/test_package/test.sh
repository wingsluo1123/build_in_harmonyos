#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cilium executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] cilium version"
cilium version && echo "✅ version OK" || {
    echo "[test] version failed, trying --help..."
    cilium --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ cilium failed both version and --help"
        exit 1
    }
}

# Validate version string content
cilium version 2>&1 | grep -q "v0.19.4" || {
    echo "❌ cilium version output does not contain v0.19.4"
    exit 1
}
echo "✅ version string validated"
