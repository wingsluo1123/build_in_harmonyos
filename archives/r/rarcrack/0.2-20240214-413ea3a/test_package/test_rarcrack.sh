#!/bin/sh
# test_rarcrack.sh — rarcrack 0.2-20240214-413ea3a 功能性测试（6 项断言式检查）
# 用法: sh test_rarcrack.sh <rarcrack-binary> <writable-workdir>
# 前 5 项为 CLI 契约验证（USAGE 文本、--help 文本、缺失文件报错路径、
# 非法 --type 告警路径、线程数钳制路径 + HMFS 重定向），第 6 项为反向
# 对照（所有用例均在 crack_start() 之前返回，WORK 内不得出现状态 *.xml，
# 证明 harness 能观察到真实行为而非伪造成功）。
# 注意：刻意只用 set -u 而不用 set -e——harness 必须在任何单项失败后继续
# 执行并始终打印 RESULT 尾行（真机门禁解析该行计数；提前退出会导致
# incomplete 而非明确失败）。

set -u

BIN="$1"
WORK="$2"
p=0
f=0

check() {
    if [ "$1" = "ok" ]; then
        echo "ok - $2"
        p=$((p+1))
    else
        echo "FAIL - $2"
        f=$((f+1))
    fi
}

mkdir -p "$WORK"

# 1) 无参数调用打印 USAGE 文本（退出 0）
"$BIN" > "$WORK/t1.out" 2>&1
if grep -q "USAGE: rarcrack" "$WORK/t1.out"; then check ok "无参数调用打印 USAGE 文本"; else check no "无参数 USAGE 文本缺失"; fi

# 2) --help 打印选项说明
"$BIN" --help > "$WORK/t2.out" 2>&1
if grep -q "Options:" "$WORK/t2.out"; then check ok "--help 打印选项说明"; else check no "--help 选项说明缺失"; fi

# 3) 缺失文件报错路径：--type zip + 不存在的文件必须报 not exists
"$BIN" "$WORK/nope.zip" --type zip > "$WORK/t3.out" 2>&1
if grep -q "not exists" "$WORK/t3.out"; then check ok "缺失文件报 not exists"; else check no "缺失文件报错路径异常"; fi

# 4) 非法 --type 告警路径：必须报 invalid parameter（随后同样因文件缺失返回）
"$BIN" "$WORK/nope2.zip" --type rarx > "$WORK/t4.out" 2>&1
if grep -q "invalid parameter" "$WORK/t4.out"; then check ok "非法 --type 报 invalid parameter"; else check no "非法 --type 告警缺失"; fi

# 5) 线程数钳制路径：--threads 20 必须钳制到 12 并提示；输出重定向到
#    HMFS 可写目录文件（鸿蒙形态：落盘文件非空）
"$BIN" "$WORK/nope3.zip" --threads 20 --type zip > "$WORK/t5.out" 2>&1
if grep -q "adjusted to 12" "$WORK/t5.out" && [ -s "$WORK/t5.out" ]; then check ok "--threads 20 钳制到 12 且 HMFS 落盘非空"; else check no "线程钳制/HMFS 落盘异常"; fi

# 6) 反向对照：以上用例均在 crack_start() 之前返回（文件缺失/参数错误），
#    loadstatus() 从未执行，WORK 内不得出现任何状态 *.xml；若出现则说明
#    二进制行为与预期不符，harness 必须判失败
found=0
for x in "$WORK"/*.xml; do
    if [ -e "$x" ]; then
        echo "unexpected status file: $x"
        found=1
    fi
done
if [ "$found" -eq 0 ]; then check ok "反向对照：WORK 内无状态 *.xml（未启动破解）"; else check no "反向对照：WORK 内出现意外 *.xml"; fi

echo "RESULT: $p passed, $f failed"
if [ "$f" -ne 0 ]; then
    exit 1
fi
exit 0
