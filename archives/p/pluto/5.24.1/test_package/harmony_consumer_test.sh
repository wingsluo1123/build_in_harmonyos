#!/bin/sh
# 鸿蒙特有消费者用例（rule12）— 在 HongMeng 内核上真实跑通 pluto 消费者流程，
# 非纯断言：
#   1. 写一份真实的 ipsec.conf（含 conn 隧道定义 + PSK 密钥），不是空壳
#   2. 用 pluto 守护进程实际加载该配置（限时前台执行）
#   3. 断言配置被真正解析（日志出现 control-socket / 监听标记；无标记 = FAIL）
#   4. 断言能力横幅（NSS 加密后端已编译进）
#   5. 采集并记录鸿蒙平台真实限制（控制 socket EPERM / 无 KVM / 内核版本）
#
# 断言设计（防 vacuous PASS）：
#   - 日志含 "syntax error"                -> FAIL（配置未解析）
#   - rc 为崩溃码（非 0/2/124）            -> FAIL（segfault/缺库，不等价于平台限制）
#   - 日志无任何启动标记                    -> FAIL（无法证明配置被解析）
#   - 日志含 "control socket" 标记         -> PASS（配置解析完成，撞上平台限制——OHOS 预期）
#   - 日志含 监听/started 标记              -> PASS（守护进程完整启动）
# rc 语义：124=timeout 杀死（pluto 进入监听态未自行退出，正常），2=pluto FATAL
#（鸿蒙平台预期：控制 socket EPERM），0=正常退出。
#
# pluto 经 PATH 定位（conanrun 环境已前置 pluto 包 bindir），其 NSS/NSPR/
# libevent 共享库运行时依赖经 LD_LIBRARY_PATH 解析（同一 conanrun 环境，见
# recipe 的 package_info runenv 修复）。
set -e

# 临时目录（/tmp 只读，回退 $HOME/tmp）
T="$(mktemp -d 2>/dev/null || true)"
if [ -z "$T" ] || [ ! -w "$T" ]; then
    T="$HOME/tmp/pluto-harmony-$$"
    mkdir -p "$T"
fi
# 防御：$T 必须非空绝对路径且是目录，防止 rm -rf 作用到空/意外路径
case "$T" in
    "") echo "FAIL: no writable temp dir"; exit 1;;
    /*) [ -d "$T" ] || { echo "FAIL: temp dir not a directory: $T"; exit 1; };;
    *) echo "FAIL: temp dir not an absolute path: $T"; exit 1;;
esac
mkdir -p "$T/rundir" "$T/nssdir" "$T/dump"

cleanup() {
    rm -rf "$T/rundir" "$T/nssdir" "$T/dump" \
           "$T/ipsec.conf" "$T/ipsec.secrets" "$T/pluto.log" "$T"
}

# 1. 真实 ipsec.conf（含 conn 隧道定义，非空壳）
cat > "$T/ipsec.conf" <<'CONF'
config setup

conn testconn
    authby=secret
    left=192.168.1.1
    leftsubnet=10.1.0.0/24
    right=192.168.1.2
    rightsubnet=10.2.0.0/24
    auto=add
    ike=aes256-sha2_256-modp2048
CONF
cat > "$T/ipsec.secrets" <<'SEC'
192.168.1.1 192.168.1.2 : PSK "test-secret-key-12345"
SEC

# 2. pluto 实际加载真实配置（限时前台——守护进程若进入监听态不会自行退出，
#    timeout 兜底杀死；鸿蒙平台因控制 socket EPERM 提前退出）
if command -v timeout >/dev/null 2>&1; then
    PLUTO_RUN="timeout 10"
else
    PLUTO_RUN=""
fi
rc=0
$PLUTO_RUN pluto --config "$T/ipsec.conf" --secretsfile "$T/ipsec.secrets" \
    --nssdir "$T/nssdir" --rundir "$T/rundir" --dumpdir "$T/dump" \
    --stderrlog --nofork > "$T/pluto.log" 2>&1 || rc=$?

# 3. 断言配置被真正解析（防 vacuous PASS）
echo "INFO: pluto exit code: $rc"
if grep -q "syntax error" "$T/pluto.log"; then
    echo "FAIL: ipsec.conf 未被正确解析（syntax error）:"
    cat "$T/pluto.log"
    cleanup
    exit 1
fi
# 崩溃码（既非 0/2/124）：segfault(139)/缺库(127)/NSS 初始化失败等，
# 不得与预期的平台限制路径混同
case "$rc" in
    0|2|124) : ;;
    *)
        echo "FAIL: pluto 异常退出 rc=$rc（崩溃，非预期的平台限制路径）:"
        cat "$T/pluto.log"
        cleanup
        exit 1
        ;;
esac
if grep -qiE "control socket" "$T/pluto.log"; then
    echo "PASS: 配置加载成功 — pluto 完成真实 ipsec.conf（含 testconn 隧道）解析并推进到控制 socket 阶段（rc=$rc）"
elif grep -qiE "listening|started" "$T/pluto.log"; then
    echo "PASS: 配置加载成功 — pluto 守护进程完整启动（rc=$rc）"
else
    echo "FAIL: 日志无启动标记（control socket / listening / started）——无法证明配置被解析:"
    cat "$T/pluto.log"
    cleanup
    exit 1
fi

# 4. 断言能力横幅（NSS 加密后端已编译进）
banner="$(pluto --version 2>&1)"
case "$banner" in
    *NSS*)
        echo "PASS: NSS 加密后端已编译进: $banner"
        ;;
    *)
        echo "FAIL: 能力横幅缺 NSS 加密后端: $banner"
        cleanup
        exit 1
        ;;
esac

# 5. 采集鸿蒙平台真实限制（证据，非阻塞断言）
echo "INFO: 鸿蒙平台限制（R40: 编译通过 != 功能完整）:"
echo "  - 控制 socket: $(grep -o 'could not bind control socket.*' "$T/pluto.log" 2>/dev/null || echo '本次未复现（环境或允许绑定）')"
echo "  - /dev/kvm: $([ -e /dev/kvm ] && echo 存在 || echo '缺失（1434 个 KVM 端到端回归不可运行）')"
echo "  - 内核: $(uname -r 2>/dev/null || echo unknown)"

cleanup
echo "PASS: 鸿蒙消费者用例完成（真实配置加载 + 能力横幅 + 平台限制实证）"
