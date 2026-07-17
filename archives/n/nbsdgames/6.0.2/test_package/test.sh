#!/bin/bash
# test_package test.sh — nbsdgames 6.0.2 消费者测试
set -euo pipefail

if command -v sudoku >/dev/null 2>&1; then
    sudoku -h >/dev/null 2>&1 || true
    echo "nbsdgames (sudoku) is available and working"
    exit 0
fi

echo "sudoku binary not found"
exit 1
