#!/bin/sh
# test_package/test.sh — smoke test for abuild
# Verifies that the abuild binary is present and responds to --version
set -euo pipefail

echo "[test] abuild --version"
abuild --version 2>&1 || {
    echo "❌ abuild --version failed"
    exit 1
}
echo "✅ abuild --version OK"

echo "[test] abuild --help"
# 完整捕获输出并校验真实退出码（避免 pipefail + head -5 的 SIGPIPE 假阳性：
# head 读满 5 行提前关闭管道会让 abuild 收到 SIGPIPE(141)，pipefail 下误报失败）
rc=0
help_out=$(abuild --help 2>&1) || rc=$?
if [ "$rc" -ne 0 ]; then
    echo "❌ abuild --help failed (exit $rc)"
    exit 1
fi
# sed -n '1,5p' 读完整个输入后才退出，不会提前关管道（与 head 不同）
printf '%s\n' "$help_out" | sed -n '1,5p'
echo "✅ abuild --help OK (shows usage)"