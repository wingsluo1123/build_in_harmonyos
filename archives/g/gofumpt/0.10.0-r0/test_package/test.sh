#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gofumpt executable
set -euo pipefail

echo "[test] gofumpt -version"
gofumpt -version

echo "[test] gofumpt format verification"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
cat > "$TMPDIR/test.go" << 'EOF'
package main

import "fmt"

func main() {
fmt.Println("hello")
}
EOF
# gofumpt should detect and report the unformatted file
gofumpt -l "$TMPDIR/test.go" > "$TMPDIR/output.txt"
if [ -s "$TMPDIR/output.txt" ]; then
    echo "✅ gofumpt detected unformatted file"
else
    echo "❌ gofumpt did not detect unformatted file"
    exit 1
fi

echo "[test] All smoke tests passed ✅"