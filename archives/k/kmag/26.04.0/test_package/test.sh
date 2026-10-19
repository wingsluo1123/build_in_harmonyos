#!/bin/sh
# test_package/test.sh — kmag 26.04.0 消费者用例执行器
# 用法: test.sh <kmag 二进制> <qimage_smoke 二进制>
# 逐例输出 TEST PASS / TEST FAIL，末尾输出 TEST SUMMARY，任一失败退出码 1。
set -u

APP="$1"
SMOKE="$2"

PASS=0
FAIL=0

record_pass() {
    echo "TEST PASS: $1"
    PASS=$((PASS + 1))
}

record_fail() {
    echo "TEST FAIL: $1"
    FAIL=$((FAIL + 1))
}

echo "[test] application binary: $APP"
if [ -x "$APP" ]; then
    record_pass "installed bin/kmag is executable"
else
    record_fail "installed bin/kmag is executable"
fi

# ---------- 用例 1: 版本门面（KAboutData / KLocalizedString / QApplication 初始化） ----------
VERSION_OUT="$("$APP" --version 2>&1)"
VERSION_RC=$?
echo "$VERSION_OUT"
if [ "$VERSION_RC" -eq 0 ] && echo "$VERSION_OUT" | grep -q "26.04.0"; then
    record_pass "kmag --version reports 26.04.0"
else
    record_fail "kmag --version reports 26.04.0"
fi

# ---------- 用例 2: 命令行帮助（KAboutData::setupCommandLine / QCommandLineParser） ----------
HELP_OUT="$("$APP" --help 2>&1)"
HELP_RC=$?
echo "$HELP_OUT" | head -5
if [ "$HELP_RC" -eq 0 ] && echo "$HELP_OUT" | grep -q "Screen magnifier"; then
    record_pass "kmag --help shows the KAboutData banner"
else
    record_fail "kmag --help shows the KAboutData banner"
fi

# ---------- 用例 3（鸿蒙特有）: KXmlGui 主窗口启动（offscreen） ----------
# kmagui.rc 以 Qt 资源形式编入 bin/kmag（qrc 前缀 /kxmlgui5/kmag），
# 无参数启动会构造 KXmlGui 主窗口；补丁 0002 修改的正是该资源里的动作表。
# 判据：进程存活进入事件循环（未在初始化/资源加载阶段退出），且日志无
# 链接器、平台插件或 XMLGUI 资源错误。
STARTUP_LOG="${TMPDIR:-/tmp}/kmag-startup-$$.log"
: > "$STARTUP_LOG" 2>/dev/null || {
    STARTUP_LOG="$PWD/kmag-startup-$$.log"
    : > "$STARTUP_LOG" 2>/dev/null || STARTUP_LOG=/dev/null
}
"$APP" > "$STARTUP_LOG" 2>&1 &
STARTUP_PID=$!
# Watchdog: after 5s terminate a still-running app, so `wait` returns the
# app's real exit status. A bare `kill -0` also succeeds on an unreaped
# zombie child, which would turn an immediate crash (e.g. SIGSEGV before
# the event loop) into a false PASS for this case.
( sleep 5; kill -TERM "$STARTUP_PID" 2>/dev/null; sleep 2; kill -KILL "$STARTUP_PID" 2>/dev/null ) &
WATCH_PID=$!
wait "$STARTUP_PID" 2>/dev/null
STARTUP_RC=$?
kill -KILL "$WATCH_PID" 2>/dev/null || true
wait "$WATCH_PID" 2>/dev/null || true
STARTUP_ALIVE=0
# 143 (TERM) / 137 (KILL) = our watchdog ended an app still alive after 5s;
# any other status means the app exited on its own before the event loop.
if [ "$STARTUP_RC" -eq 143 ] || [ "$STARTUP_RC" -eq 137 ]; then
    STARTUP_ALIVE=1
fi
if [ "$STARTUP_ALIVE" -eq 1 ] && ! grep -qE 'cannot open shared object file|error while loading shared libraries|symbol lookup error|undefined symbol|Could not find the Qt platform plugin|cannot find .rc file|No such object|Action .file_print. not found' "$STARTUP_LOG" 2>/dev/null; then
    record_pass "kmag main window starts offscreen (KXmlGui resources loaded)"
else
    record_fail "kmag main window starts offscreen (KXmlGui resources loaded)"
    echo "startup exit status: $STARTUP_RC"
    head -20 "$STARTUP_LOG" 2>/dev/null
fi
[ "$STARTUP_LOG" = /dev/null ] || rm -f "$STARTUP_LOG"

# ---------- 用例 4: 快照导出链路（QImage -> QPainter -> QImageWriter -> QImageReader） ----------
SMOKE_OUT="$(mktemp 2>/dev/null)"
if [ -z "$SMOKE_OUT" ] || [ ! -f "$SMOKE_OUT" ]; then
    SMOKE_OUT="${TMPDIR:-/tmp}/kmag-smoke-$$.log"
    : > "$SMOKE_OUT" 2>/dev/null || SMOKE_OUT=""
fi
SMOKE_PASS=0
SMOKE_FAIL=0
if [ -z "$SMOKE_OUT" ]; then
    echo "[test] snapshot export log path is not writable"
    SMOKE_RC=1
else
    "$SMOKE" > "$SMOKE_OUT" 2>&1
    SMOKE_RC=$?
    cat "$SMOKE_OUT"
    SMOKE_PASS=$(grep -c '^TEST PASS:' "$SMOKE_OUT" 2>/dev/null || true)
    SMOKE_FAIL=$(grep -c '^TEST FAIL:' "$SMOKE_OUT" 2>/dev/null || true)
    SMOKE_PASS=${SMOKE_PASS:-0}
    SMOKE_FAIL=${SMOKE_FAIL:-0}
    PASS=$((PASS + SMOKE_PASS))
    FAIL=$((FAIL + SMOKE_FAIL))
    rm -f "$SMOKE_OUT"
fi
if [ "$SMOKE_RC" -ne 0 ] && [ "$SMOKE_FAIL" -eq 0 ]; then
    record_fail "snapshot export consumer process exited with $SMOKE_RC"
fi
if [ "$SMOKE_PASS" -eq 0 ] && [ "$SMOKE_FAIL" -eq 0 ]; then
    record_fail "snapshot export consumer produced no case results"
fi

# ---------- 用例总数核对 ----------
# MANIFEST.yml 声明 check_count: 11（应用侧 4 + 快照导出 7）。qimage_smoke
# 若提前返回，PASS+FAIL 会小于声明值；不核对就会「少跑仍全绿」。
EXPECTED_CHECKS=11
TOTAL_CHECKS=$((PASS + FAIL))
if [ "$TOTAL_CHECKS" -ne "$EXPECTED_CHECKS" ]; then
    record_fail "expected $EXPECTED_CHECKS consumer checks, observed $TOTAL_CHECKS"
fi

echo "TEST SUMMARY: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ] || [ "$PASS" -eq 0 ]; then
    exit 1
fi
exit 0
