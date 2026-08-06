#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for github-mcp-server executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] github-mcp-server --version"
github-mcp-server --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    github-mcp-server --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ github-mcp-server failed both --version and --help"
        exit 1
    }
}

echo "[test] mcpcurl --help"
mcpcurl --help > /dev/null 2>&1 && echo "✅ mcpcurl --help OK" || {
    echo "[test] mcpcurl --help failed (non-fatal)"
}
