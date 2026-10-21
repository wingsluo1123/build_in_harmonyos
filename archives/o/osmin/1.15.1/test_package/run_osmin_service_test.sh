#!/bin/sh
# osmin 消费者测试：真实执行被测包的产物（R34，非空壳断言）
#
# 用法: run_osmin_service_test.sh <osmin二进制> <日志路径> <HOME 目录>
#
# 为什么走无头服务分支：osmin 是 Qt6 Quick 图形应用，没有 --version/--help 之类
# 的命令行开关；src/osmin.cpp:69 定义的 `-service` 开关（:154 分派）走
# QCoreApplication + QRemoteObjectHost 本地套接字（SERVICE_URL），不依赖显示
# 设备与 DBus，把定位/罗盘/轨迹服务常驻后台 —— 这是同一产物的第二个真实消费者
# 入口，也是本测试选取的执行路径。
#
# 通过判据：
#   rc=0           服务自行干净退出
#   rc=124 / 143   完成 Qt 初始化并进入事件循环，存活到超时（服务在运行）
# 其余退出码（含崩溃 139/134）判失败；启动日志出现动态库加载失败、符号解析
# 失败、崩溃、FATAL 标记一律判失败。
#
# 附加断言（真实副作用）：服务启动时会用 PlatformExtras::getDataDir() 的
# HomeLocation 分支创建自身数据目录（src/osmin.cpp: mkpath(APP_NAME) / mkpath(GPX)），
# 因此 HOME 下必须出现新建目录 —— 否则说明数据目录初始化失败。
set -u

BIN="${1:?缺少 osmin 二进制路径}"
LOG="${2:?缺少日志路径}"
HOME_DIR="${3:?缺少 HOME 目录}"

if [ ! -x "$BIN" ]; then
    echo "[test] 产物不可执行: $BIN"
    exit 1
fi

rm -rf "$HOME_DIR"
mkdir -p "$HOME_DIR"

# 收尾清理：无论成功失败都不在源码树里留下临时 HOME（CI 垃圾文件门禁）
cleanup() { rm -rf "$HOME_DIR"; }
trap cleanup EXIT INT TERM

rc=0
HOME="$HOME_DIR" QT_QPA_PLATFORM=offscreen timeout 20 "$BIN" -service > "$LOG" 2>&1 || rc=$?

case "$rc" in
    0|124|143)
        ;;
    *)
        echo "[test] osmin -service 提前退出，rc=$rc"
        sed -n '1,60p' "$LOG"
        exit 1
        ;;
esac

if grep -qiE 'cannot open shared object|symbol lookup error|undefined symbol|segmentation fault|core dumped|FATAL' "$LOG"; then
    echo "[test] 启动日志出现致命错误:"
    sed -n '1,60p' "$LOG"
    exit 1
fi

created=$(find "$HOME_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tr '\n' ' ')
if [ -z "$created" ]; then
    echo "[test] 服务未创建任何数据目录（$HOME_DIR 为空），数据目录初始化失败"
    sed -n '1,60p' "$LOG"
    exit 1
fi

echo "[test] osmin -service 启动正常（rc=$rc）"
echo "[test] 已创建数据目录: ${created% }"
echo "[test] 启动日志前 15 行:"
sed -n '1,15p' "$LOG"
