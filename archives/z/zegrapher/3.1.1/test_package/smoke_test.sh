#!/bin/sh
# smoke_test.sh — zeGrapher 3.1.1 test_package 测试源（L0c 门禁）
#
# 真实调用被测包打包的 ZeGrapher 二进制并断言可观察结果（不是空壳）：
#   T1: 二进制能启动 QApplication（offscreen 平台）且正常退出
#   T2: 二进制是有效的 aarch64 ELF（架构匹配，非空壳产物）
# 上游 zeGrapher 无测试套件（无 tests/ 目录、.pro 无 test target，
# 见 notes.md 清点），此冒烟测试为按 R51 补全的鸿蒙特有测试。
#
# 用法: sh smoke_test.sh <ZeGrapher 二进制路径>
# 退出码: 0=全部断言通过; 1=断言失败; 2=用法/参数错误
# 仅 set -u：T1 需捕获 timeout 的非零 rc（124）作为存活断言，-e 会中断采集
set -u
BIN="${1:-}"

[ -n "$BIN" ] && [ -f "$BIN" ] || { echo "usage: $0 <zegrapher-binary>"; exit 2; }

fail=0
chk() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi }

echo "--- zeGrapher 3.1.1 test_package smoke test (QT_QPA_PLATFORM=offscreen) ---"

# T2: ELF 架构检查（aarch64）
if command -v file >/dev/null 2>&1; then
    file "$BIN" | grep -qi "arm.*aarch64\|aarch64" && r=0 || r=1
    chk "T2 二进制为 aarch64 ELF" "$r"
else
    head -c 20 "$BIN" | od -An -tx1 | grep -q "7f 45 4c 46" && r=0 || r=1
    chk "T2 二进制为有效 ELF（无 file 命令，检查魔数）" "$r"
fi

# T1: offscreen 启动 QApplication 后正常退出。
# zeGrapher 直接进入 GUI 主循环（无 CLI 参数处理），offscreen 平台下
# 无法交互退出 —— 用 timeout 限时运行，存活到超时 = 应用启动成功
# （崩溃/缺库/平台插件失败会在 1s 内以非 0 退出）。
timeout 5 "$BIN" >/dev/null 2>&1
rc=$?
# rc=124 (timeout 到期杀掉) 或 rc=0 都视为启动成功；其余 rc = 启动失败
if [ "$rc" = "124" ] || [ "$rc" = "0" ]; then r=0; else r=1; fi
chk "T1 offscreen 启动 QApplication 存活至超时(rc=$rc, 期望 0/124)" "$r"

if [ "$fail" = "0" ]; then echo "--- smoke test: ALL PASS ---"; else echo "--- smoke test: FAILED ---"; fi
exit $fail
