#!/bin/sh
# test_package 冒烟测试：启动 mystiq GUI（headless QPA），验证 Qt5 运行时链闭合。
# 用法: test_mystiq.sh <mystiq-binary> <qt-plugin-path> <qml-import-path>
set -u

EXE="$1"
QT_PLUGIN_PATH_ARG="${2:-}"
QML2_IMPORT_PATH_ARG="${3:-}"

[ -x "$EXE" ] || { echo "[fail] mystiq binary not executable: $EXE"; exit 1; }

export QT_QPA_PLATFORM=offscreen
[ -n "$QT_PLUGIN_PATH_ARG" ] && export QT_PLUGIN_PATH="$QT_PLUGIN_PATH_ARG"
[ -n "$QML2_IMPORT_PATH_ARG" ] && export QML2_IMPORT_PATH="$QML2_IMPORT_PATH_ARG"
XDG_RUNTIME_DIR="$(pwd)/xdg-runtime"
mkdir -p "$XDG_RUNTIME_DIR"
export XDG_RUNTIME_DIR

echo "[info] launching $EXE (QT_QPA_PLATFORM=offscreen)"
"$EXE" &
PID=$!

# GUI 应用启动后常驻事件循环：存活 6s 视为 Qt5 初始化成功
i=0
while [ $i -lt 12 ]; do
    sleep 0.5
    if ! kill -0 $PID 2>/dev/null; then
        wait $PID
        echo "[fail] mystiq exited prematurely (rc=$?)"
        exit 1
    fi
    i=$((i+1))
done

kill $PID 2>/dev/null
wait $PID 2>/dev/null
echo "[ok] mystiq stayed alive for 6s: Qt5 GUI init OK (offscreen QPA)"
exit 0
