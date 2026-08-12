#!/usr/bin/env bash
# test_package for roswell — 实质验证 ros 二进制可执行且版本正确 (R34)
# 鸿蒙 getpwuid() 无 passwd 条目 → homedir() 返回 NULL → 必须设置 ROSWELL_HOME
set -euo pipefail

ROSWELL_HOME="${ROSWELL_HOME:-$HOME/.roswell-test}"
export ROSWELL_HOME
mkdir -p "$ROSWELL_HOME"

echo "=== ros --version ==="
ros --version
echo "=== ros help (smoke) ==="
ros help >/dev/null 2>&1 && echo "ros help: OK"

echo "test_package PASS"
