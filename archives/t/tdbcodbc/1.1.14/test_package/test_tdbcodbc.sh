#!/bin/sh
# test_tdbcodbc.sh — tdbcodbc/1.1.14 消费者测试入口（shell 包装）
#
# CI L0c 要求 test_package/ 下存在 .c/.cpp/.cc/.cxx/.sh/.py 测试源文件；
# tdbcodbc 是 Tcl 扩展包，断言实现见同目录 test_tdbcodbc.tcl，由本脚本以 tclsh 执行。
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

exec tclsh8.6 "$SCRIPT_DIR/test_tdbcodbc.tcl"
