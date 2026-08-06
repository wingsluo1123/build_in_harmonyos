#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for Go toolchain
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] go version"
go version && echo "✅ go version OK" || {
    echo "❌ go version failed"
    exit 1
}

echo "[test] go env GOROOT"
go env GOROOT && echo "✅ go env GOROOT OK" || {
    echo "❌ go env GOROOT failed"
    exit 1
}

echo "[test] go env GOVERSION"
go env GOVERSION && echo "✅ go env GOVERSION OK" || {
    echo "❌ go env GOVERSION failed"
    exit 1
}
