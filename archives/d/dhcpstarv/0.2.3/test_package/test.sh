#!/bin/bash
# test_package/test.sh — 验证 dhcpstarv 二进制功能正常
# dhcpstarv --help 打印版本 0.2.3 与 Usage 并退出码 0（见 src/main.c main()）
# 用法: test.sh <dhcpstarv 二进制路径>
set -euo pipefail

BIN="${1:-dhcpstarv}"

if "$BIN" --help 2>&1 | grep -q "0.2.3"; then
    echo "        [ok] dhcpstarv --help prints version 0.2.3"
else
    echo "        [fail] dhcpstarv --help did not print version"
    exit 1
fi
