#!/bin/sh
# test_package/test.sh — 消费者冒烟测试：真实导入 pydl 并断言版本
# 验证打包的 site-packages 布局可被 Python 发现（R34：不得为空壳测试）
set -eu

PYTHON="${PYTHON:-python3}"
SITE="${PYTHONPATH:-}"

echo "[test] import pydl (PYTHONPATH=$SITE)"
out="$("$PYTHON" -c "import pydl; print(pydl.__version__)" 2>&1)" || {
    echo "❌ import pydl 失败 (exit=$?)"
    exit 1
}
echo "pydl version: $out"

case "$out" in
    "1.0.1")
        echo "✅ pydl 版本断言通过 (1.0.1)"
        ;;
    *)
        echo "❌ pydl 版本断言失败: $out"
        exit 1
        ;;
esac
exit 0
