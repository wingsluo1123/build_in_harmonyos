#!/data/service/hnp/bin/bash
# test_package/test.sh — rtkit 安装产物在真机上的执行契约
#
# rtkit 不产出库，只产出可执行程序，因此 test_package 直接执行安装后的
# 二进制并断言其行为（R34：禁止空壳测试）。
#
# 覆盖：
#   1. rtkit-daemon / rtkitctl 为 OHOS aarch64 ELF 且可被内核装载执行
#   2. 两个 CLI 的接口契约（--help / --version 输出）
#   3. daemon 的 root 特权契约：非 root 调用必须明确拒绝并退出非零
#
# 注意：本沙箱 /tmp 只读，故全部断言走 shell 变量，不落任何临时文件。
set -euo pipefail

DAEMON="${RTKIT_DAEMON:-rtkit-daemon}"
CTL="${RTKIT_CTL:-rtkitctl}"

fail() {
    echo "❌ $*" >&2
    exit 1
}

echo "== 1. daemon 可执行且报告版本 =="
daemon_version="$("$DAEMON" --version 2>&1)" \
    || fail "rtkit-daemon --version 执行失败（未签名 / 架构不符？）：$daemon_version"
case "$daemon_version" in
    *0.14*) ;;
    *) fail "rtkit-daemon --version 未报告 0.14：$daemon_version" ;;
esac
echo "✅ rtkit-daemon $daemon_version"

echo "== 2. daemon CLI 契约：D-Bus 服务选项齐备 =="
daemon_help="$("$DAEMON" --help 2>&1)" || fail "rtkit-daemon --help 执行失败"
for opt in '--user-name' '--max-realtime-priority' '--min-nice-level' \
           '--rttime-usec-max' '--scheduling-policy' '--no-canary' '--no-chroot'; do
    case "$daemon_help" in
        *"$opt"*) ;;
        *) fail "rtkit-daemon --help 缺少选项 $opt" ;;
    esac
done
echo "✅ rtkit-daemon 暴露 7 项关键选项"

echo "== 3. rtkitctl CLI 契约：控制命令齐备 =="
ctl_help="$("$CTL" --help 2>&1)" || fail "rtkitctl --help 执行失败"
for cmd in '--reset-known' '--reset-all' '--start' '--exit' '--suspend' '--resume'; do
    case "$ctl_help" in
        *"$cmd"*) ;;
        *) fail "rtkitctl --help 缺少命令 $cmd" ;;
    esac
done
echo "✅ rtkitctl 暴露 6 项控制命令"

echo "== 4. daemon root 特权契约 =="
if [ "$(id -u 2>/dev/null)" = "0" ]; then
    echo "⏭  当前为 root，跳过非特权拒绝断言"
else
    set +e
    noroot_out="$("$DAEMON" --stderr 2>&1)"
    rc=$?
    set -e
    case "$noroot_out" in
        *"Need to be run as root"*) ;;
        *) fail "非 root 运行未被拒绝：$noroot_out" ;;
    esac
    [ "$rc" -ne 0 ] || fail "非 root 运行应当退出非零，实测 rc=0"
    echo "✅ 非 root 被拒绝并退出 rc=$rc"
fi

echo "✅ rtkit test_package 全部通过"
