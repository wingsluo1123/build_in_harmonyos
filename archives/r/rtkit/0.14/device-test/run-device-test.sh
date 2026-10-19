#!/data/service/hnp/bin/bash
# rtkit 鸿蒙真机端到端测试（在 HarmonyOS PC 本机执行）
#
# 目标：在真机上实际跑通 rtkit 的功能流程 ——
#   消费端(rtkit 客户端库 rtkit.c) → D-Bus 系统总线 → rtkit-daemon → 回包
#
# 环境前提（本沙箱的既有限制，详见 notes.md）：
#   1) 无 root / 无 sudo / user namespace 被 seccomp 拦截 → 用 gate-shim 过
#      rtkit-daemon 的启动门禁；
#   2) 本机没有 D-Bus 总线守护进程，且制品仓的 dbus 包只含客户端库 →
#      需自备一个 dbus-daemon（DBUS_DAEMON 指定）；
#   3) 本机 uid 无 passwd 条目 → 用 passwd-shim 让总线能完成握手；
#   4) 真机对 ELF 强制签名 → 三个产物 + 两个 shim 都必须签名后才能执行。
#
# 用法：
#   RTKIT_PKG=<已安装的 rtkit 包目录> DBUS_DAEMON=<dbus-daemon 路径> \
#       bash run-device-test.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
RTKIT_PKG="${RTKIT_PKG:?需要指定 rtkit 包目录（含 bin/ 与 libexec/）}"
DBUS_DAEMON="${DBUS_DAEMON:?需要指定可执行的 dbus-daemon 路径}"
CLANG="${CLANG:-/data/service/hnp/bin/clang}"
SIGNER="${SIGNER:-/data/service/hnp/bin/binary-sign-tool}"
OBJCOPY="${OBJCOPY:-/data/service/hnp/bin/llvm-objcopy}"

WORK="$(mktemp -d "${TMPDIR:-$HOME/tmp}/rtkit-device-test.XXXXXX")"
BUS_PID=""
DAEMON_PID=""
cleanup() {
    [ -n "$DAEMON_PID" ] && kill "$DAEMON_PID" 2>/dev/null || true
    [ -n "$BUS_PID" ] && kill "$BUS_PID" 2>/dev/null || true
    wait 2>/dev/null || true
    # R10: 工作区建在 $TMPDIR/$HOME 下并随脚本退出清理，避免残留物污染归档
    if [ "${KEEP_WORK:-0}" = "1" ]; then
        echo "   [KEEP_WORK=1] 保留取证目录: $WORK"
    else
        rm -rf "$WORK" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

sign() {
    "$OBJCOPY" --remove-section .codesign "$1" 2>/dev/null || true
    "$SIGNER" sign -inFile "$1" -outFile "$1" -selfSign 1 > /dev/null 2>&1
    chmod +x "$1"
}

echo "== 0. 编译并签名两个测试 shim =="
"$CLANG" -shared -fPIC -O2 -o "$WORK/libgate.so"   "$HERE/gate-shim.c"
"$CLANG" -shared -fPIC -O2 -o "$WORK/libpasswd.so" "$HERE/passwd-shim.c"
sign "$WORK/libgate.so"
sign "$WORK/libpasswd.so"

echo "== 1. 启动私有 D-Bus 系统总线 =="
cp "$DBUS_DAEMON" "$WORK/dbus-daemon"
sign "$WORK/dbus-daemon"
LD_PRELOAD="$WORK/libpasswd.so" "$WORK/dbus-daemon" \
    --config-file="$HERE/bus.conf" --nofork --print-address \
    > "$WORK/bus.addr" 2> "$WORK/bus.err" &
BUS_PID=$!
for _ in $(seq 1 50); do
    [ -s "$WORK/bus.addr" ] && break
    sleep 0.2
done
ADDR="$(head -1 "$WORK/bus.addr" 2>/dev/null || true)"
[ -n "$ADDR" ] || { echo "❌ 总线启动失败：$(cat "$WORK/bus.err" 2>/dev/null)"; exit 1; }
echo "✅ $ADDR"

export DBUS_SYSTEM_BUS_ADDRESS="$ADDR"
CLIENT_ENV=(env "LD_PRELOAD=$WORK/libpasswd.so")

echo "== 2. 启动 rtkit-daemon 并注册 org.freedesktop.RealtimeKit1 =="
env "LD_PRELOAD=$WORK/libpasswd.so $WORK/libgate.so" \
    "$RTKIT_PKG/libexec/rtkit-daemon" \
    --stderr --debug --no-chroot --no-drop-privileges \
    --no-limit-resources --no-canary \
    > "$WORK/daemon.log" 2>&1 &
DAEMON_PID=$!
for _ in $(seq 1 50); do
    grep -q "Running." "$WORK/daemon.log" 2>/dev/null && break
    sleep 0.2
done
grep -q "Running." "$WORK/daemon.log" \
    || { echo "❌ daemon 未启动：$(head -5 "$WORK/daemon.log")"; exit 1; }
echo "✅ daemon Running"

echo "== 3. 消费端：rtkit 客户端库经 D-Bus 读取 daemon 属性 =="
"${CLIENT_ENV[@]}" "$RTKIT_PKG/libexec/installed-tests/rtkit/rtkit-test" \
    > "$WORK/consumer.log" 2>&1 || true
cat "$WORK/consumer.log"

# 断言：客户端读到的值必须等于 daemon 侧默认值（20 / -15 / 200000）
grep -q "Max realtime priority is: 20"        "$WORK/consumer.log" || { echo "❌ 未取到 MaxRealtimePriority"; exit 1; }
grep -q "Min nice level is: -15"               "$WORK/consumer.log" || { echo "❌ 未取到 MinNiceLevel"; exit 1; }
grep -q "Rttime limit is: 200000 ns"           "$WORK/consumer.log" || { echo "❌ 未取到 RTTimeUSecMax"; exit 1; }

echo "== 4. 消费端：rtkitctl 控制命令（D-Bus 方法调用） =="
for cmd in --reset-known --reset-all --suspend --resume; do
    "${CLIENT_ENV[@]}" "$RTKIT_PKG/bin/rtkitctl" "$cmd" \
        || { echo "❌ rtkitctl $cmd 失败"; exit 1; }
    echo "✅ rtkitctl $cmd rc=0"
done

echo "== 5. 服务端证据：daemon 侧确实在处理请求 =="
grep -m1 "Supervising" "$WORK/daemon.log" || true

echo "✅ rtkit 真机端到端测试全部通过"
echo "   （测试夹具非交付物：两个 shim + 私有总线配置见 device-test/，dbus-daemon 来源见 notes.md §5.3）"
