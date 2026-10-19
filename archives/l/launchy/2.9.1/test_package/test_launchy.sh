#!/bin/sh
# launchy 2.9.1 消费者自检脚本（test_package 调用）
# P2 修复：R01 版把动态依赖检查全部降级为 warn 后无条件 PASS（恒 PASS 空壳）。
# 本版改为严格检查：set -euo pipefail + 真实依赖检查，任一核心库缺失即失败退出。
#
# 检查项：
#  1) bin/launchy 存在且为 aarch64 ELF（e_machine=183=0xB7）
#  2) readelf -d 的 DT_NEEDED 必须全部命中核心 Qt5/X11/libc++ 动态依赖，缺一即失败
#     （对 Qt5/X11 链接退化、制品不可用有真实鉴别力）
#  3) 完整 GUI 事件循环需要显示服务器，OHOS 无显示环境无法启动 GUI 进程，
#     记录为平台限制（与 baka 先例一致），不伪造通过；运行时路径验证
#     由 test.c 消费者程序以 offscreen 平台真实触发 QLockFile 单实例锁完成。
set -euo pipefail

EXE="${1:-}"
if [ -z "$EXE" ] || [ ! -f "$EXE" ]; then
    echo "[fail] launchy 二进制缺失: $EXE" >&2
    exit 1
fi

FAIL=0

# 1) aarch64 ELF 断言（e_machine=183=0xB7）
if [ "$(od -An -N4 -tx1 "$EXE" | tr -d ' \n')" != "7f454c46" ]; then
    echo "[fail] launchy 不是 ELF 文件" >&2
    FAIL=1
else
    echo "[ok] launchy ELF 魔数: $EXE"
fi
MACHINE=$(od -An -j18 -N2 -tu2 "$EXE" | tr -d ' ')
if [ "$MACHINE" != "183" ]; then
    echo "[fail] launchy 不是 aarch64 ELF (e_machine=$MACHINE)" >&2
    FAIL=1
else
    echo "[ok] launchy ELF aarch64 (e_machine=183)"
fi

# 2) DT_NEEDED 严格解析（readelf 通用性优于 ldd，OHOS 无 ldd）
READELF=$(command -v readelf || echo /usr/bin/readelf)
NEEDED=$( "$READELF" -d "$EXE" 2>/dev/null | awk '/NEEDED/ {print $NF}' | tr -d '[]' | tr '\n' ' ' )
echo "[info] DT_NEEDED: $NEEDED"
for key in libQt5Core.so libQt5Widgets.so libQt5Gui.so libQt5Network.so libX11.so libxcb.so libc++_shared.so; do
    case " $NEEDED " in
        *" $key"*)
            echo "[ok] 动态依赖命中: $key" ;;
        *)
            echo "[fail] DT_NEEDED 缺失核心库: $key（Qt5/X11 链接退化或制品不可用）" >&2
            FAIL=1 ;;
    esac
done

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] 消费者验证失败：见上方 [fail] 项" >&2
    exit 1
fi

echo "[pass] 消费者验证 PASS (ELF aarch64 + DT_NEEDED 全部命中)"
exit 0
