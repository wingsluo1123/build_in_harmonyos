#!/bin/sh
# jalv 消费者测试驱动（真实执行型，R34）——由 test_package/conanfile.py 的
# test() 以 conanrun 环境调用。语义与原内嵌 Python 断言一一对应：
#   1) 版本串：确认跑的是 jalv 1.10.0 本体（-V 退出码为 81，按内容断言）；
#   2) usage：必须保留宿主契约参数 PLUGIN_STATE；
#   3) 真实宿主链路：经 LV2_PATH 加载 mda-lv2 真实插件 bundle；
#   4) 无音频服务器时必须优雅失败（rc=1 且打印 Failed to connect to audio
#      system），绝不允许 SIGSEGV（rc=139，NULL 守卫补丁的回归守卫）；
#      本机存在音频服务器时 jalv 跑满 20s 被 timeout 收掉（rc=124），属通过。
# 用法: sh test_app.sh <lv2_dir> <log_prefix>
set -u

LV2_DIR="${1:?usage: test_app.sh <lv2_dir> <log_prefix>}"
LOGPFX="${2:?usage: test_app.sh <lv2_dir> <log_prefix>}"

PLUGIN_URI="http://drobilla.net/plugins/mda/Delay"
RC_NO_AUDIO=1
RC_TIMEOUT=124
RC_SIGSEGV=139

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

# 1) 版本串（-V/-h 打印后返回，退出码非 0 属上游行为，忽略 rc 只看内容）
jalv -V > "${LOGPFX}.version" 2>&1 || true
grep -q "jalv 1.10.0" "${LOGPFX}.version" \
    || fail "unexpected version output: $(cat "${LOGPFX}.version")"

# 2) usage 必须提到宿主契约参数 PLUGIN_STATE
jalv -h > "${LOGPFX}.help" 2>&1 || true
grep -q "Usage: jalv" "${LOGPFX}.help" || fail "unexpected help output"
grep -q "PLUGIN_STATE" "${LOGPFX}.help" \
    || fail "help lost the host contract argument PLUGIN_STATE"

# 3) 真实插件 bundle 必须存在
[ -d "$LV2_DIR" ] || fail "mda-lv2 bundle missing: $LV2_DIR"

# 4) 真实宿主链路。20s 上限防挂死；日志重定向到文件，绝不接管道
#    （SIGPIPE 会让被测进程提前死掉，测试失真）。
LV2_PATH="$LV2_DIR" timeout 20 jalv -i "$PLUGIN_URI" > "${LOGPFX}.host" 2>&1
rc=$?

# 崩溃回归守卫（补丁前此处为 139）
[ "$rc" -eq "$RC_SIGSEGV" ] \
    && fail "jalv crashed (SIGSEGV) instead of failing gracefully when no audio server is available: $(cat "${LOGPFX}.host")"

# 插件必须真的被解析加载
grep -q "Plugin: $PLUGIN_URI" "${LOGPFX}.host" \
    || fail "jalv did not load the mda-lv2 plugin: $(cat "${LOGPFX}.host")"

if [ "$rc" -eq "$RC_NO_AUDIO" ]; then
    # CI 常态：无音频服务器 → 必须优雅失败而不是崩溃
    grep -q "Failed to connect to audio system" "${LOGPFX}.host" \
        || fail "missing graceful backend error message: $(cat "${LOGPFX}.host")"
elif [ "$rc" -eq "$RC_TIMEOUT" ]; then
    echo "OK: audio server present, jalv ran until the 20s guard timeout"
else
    fail "unexpected jalv exit code $rc: $(cat "${LOGPFX}.host")"
fi

echo "OK: jalv 1.10.0 consumer contract passed (rc=$rc, no SIGSEGV)"
