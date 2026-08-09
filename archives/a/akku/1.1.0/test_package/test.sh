#!/bin/sh
# test_package 冒烟测试：验证 akku CLI 可执行且输出正确版本。
# akku 用 version 子命令（非 --version，srfi-37 args-fold 解析）。
set -e

VERSION_OUTPUT="$(akku version 2>/dev/null)"
echo "akku version => ${VERSION_OUTPUT}"

case "$VERSION_OUTPUT" in
    *1.1.0*)
        echo "PASS: akku version 输出匹配 1.1.0"
        ;;
    *)
        echo "FAIL: 期望包含 1.1.0，实际输出: ${VERSION_OUTPUT}" >&2
        exit 1
        ;;
esac
