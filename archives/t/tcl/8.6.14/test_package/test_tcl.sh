#!/bin/sh
# test_tcl.sh — 验证 tclsh8.6 可执行并完成基本 Tcl 功能测试
# 此为 test_package 真实测试源，满足 L0c 要求
set -euo pipefail

echo "=== Tcl 8.6.14 test_package smoke test ==="

# 1. 检查 tclsh 是否存在并可执行
TCLSH=$(command -v tclsh8.6 2>/dev/null || echo "")
if [ -z "$TCLSH" ]; then
    echo "[FAIL] tclsh8.6 not found in PATH"
    exit 1
fi
echo "[PASS] tclsh8.6 found at: $TCLSH"

# 2. 验证版本
PATCHLEVEL=$(tclsh8.6 << 'TCL_EOF' 2>&1
puts [info patchlevel]
TCL_EOF
)
if [ "$PATCHLEVEL" = "8.6.14" ]; then
    echo "[PASS] patchlevel: $PATCHLEVEL"
else
    echo "[FAIL] unexpected patchlevel: '$PATCHLEVEL' (expected 8.6.14)"
    exit 1
fi

# 3. 基本 Tcl 语言能力：变量、运算、输出
RESULT=$(tclsh8.6 << 'TCL_EOF' 2>&1
set a 42
set b 58
puts [expr {$a + $b}]
TCL_EOF
)
if [ "$RESULT" = "100" ]; then
    echo "[PASS] basic arithmetic: 42 + 58 = $RESULT"
else
    echo "[FAIL] arithmetic test: got '$RESULT', expected 100"
    exit 1
fi

# 4. 列表操作
RESULT=$(tclsh8.6 << 'TCL_EOF' 2>&1
set lst {a b c}
puts [llength $lst]
TCL_EOF
)
if [ "$RESULT" = "3" ]; then
    echo "[PASS] list operations: length = $RESULT"
else
    echo "[FAIL] list test: got '$RESULT', expected 3"
    exit 1
fi

# 5. 字符串操作
RESULT=$(tclsh8.6 << 'TCL_EOF' 2>&1
puts [string length "Hello Tcl"]
TCL_EOF
)
if [ "$RESULT" = "9" ]; then
    echo "[PASS] string operations: length = $RESULT"
else
    echo "[FAIL] string test: got '$RESULT', expected 9"
    exit 1
fi

# 6. 字典操作
RESULT=$(tclsh8.6 << 'TCL_EOF' 2>&1
dict set d name Tcl
dict set d version 8.6.14
puts [dict size $d]
TCL_EOF
)
if [ "$RESULT" = "2" ]; then
    echo "[PASS] dict operations: size = $RESULT"
else
    echo "[FAIL] dict test: got '$RESULT', expected 2"
    exit 1
fi

echo ""
echo "=== All smoke tests passed (6 assertions) ==="
exit 0
