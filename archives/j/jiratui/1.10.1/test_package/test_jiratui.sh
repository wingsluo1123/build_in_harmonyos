#!/bin/sh
# test_package/test_jiratui.sh — jiratui 消费者测试
# L0c: test_package/ 下的测试源文件
# 验证 jiratui 命令可执行且 version 输出正确

set -e

JIRATUI_BIN="${1:-jiratui}"

if command -v "$JIRATUI_BIN" >/dev/null 2>&1; then
    VERSION_OUTPUT=$("$JIRATUI_BIN" version 2>&1)
    echo "jiratui version output: $VERSION_OUTPUT"
    echo "$VERSION_OUTPUT" | grep -q "1.10.1" || {
        echo "FAIL: version 1.10.1 not found in output"
        exit 1
    }
    echo "PASS: jiratui version is 1.10.1"
else
    # Fallback: test Python import
    python -c "import jiratui; print('jiratui imported OK')" 2>&1 || {
        echo "FAIL: jiratui not importable"
        exit 1
    }
    echo "PASS: jiratui package imported"
fi
