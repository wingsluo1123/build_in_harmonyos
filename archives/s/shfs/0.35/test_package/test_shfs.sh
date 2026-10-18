#!/bin/sh
# test_package/test_shfs.sh — shfs 0.35 鸿蒙 PC 适配验证套件
#
# 9 个用例，断言按用例级 pass/fail 计（用例数 == 断言数 == 9，与 MANIFEST.yml、
# PR 正文「适配后测试用例统计」三处保持一致）；用例内部合计约 30 个检查点，
# 任一失败该用例记 FAIL。
# 消费者视角：只调用打包产物 bin/shfsmount、bin/shfsumount 和包内 res/shfs/ 下
# 随包分发的上游测试脚本，不依赖源码树。
#
# 编号口径:
#   U1/U2  上游自带测试用例（shfsmount/shell-test.in、shfsmount/perl-test.in）
#   H1/H2  鸿蒙特有测试（端到端消费者用例）
#   C1..C5 新增 CLI 契约用例
#
# 不用 set -e：本套件把退出码当作一等公民的断言对象（H1 断言 SIGSYS=159、C3/C4 断言
# 2、C5 断言 1/0/1），-e 会在采集 $? 之前就把用例杀掉。pipefail 无副作用（套件内无
# 命令管道，仅 || 短路），照规范带上以防御将来引入的管道。
set -uo pipefail

PKG=${1:-}
if [ -z "$PKG" ]; then
    echo "usage: test_shfs.sh <package_folder>"
    exit 1
fi

BIN="$PKG/bin"
RES="$PKG/res/shfs"
# 上游 probe 脚本要在平台 shell 里跑：/bin/sh 正是 shfsmount 自身 execvp 的那个 shell
SH=${SH:-/bin/sh}

if [ ! -x "$BIN/shfsmount" ] || [ ! -x "$BIN/shfsumount" ]; then
    echo "packaged binaries missing under $BIN"
    exit 1
fi

# perl-test.in 要求 PATH 上找得到 perl；鸿蒙设备的 perl 在 hnp 目录
if ! command -v perl >/dev/null 2>&1; then
    PATH="$PATH:/data/service/hnp/bin"
    export PATH
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/shfsX-XXXXXXXX") || exit 1
trap 'rm -rf "$WORK"' EXIT INT TERM

CASES=0
FAILED=0
expect() {
    _id=$1
    shift
    CASES=$((CASES + 1))
    if "$@" >"$WORK/$_id.log" 2>&1; then
        printf '[PASS] %s\n' "$_id"
    else
        printf '[FAIL] %s\n' "$_id"
        sed 's/^/        /' "$WORK/$_id.log"
        FAILED=$((FAILED + 1))
    fi
}

# 挂载表是否被这次运行污染（新增以 $1 为挂载点的条目，或出现 shfs 文件系统类型）
mount_untouched() {
    if grep -qF "$1" /proc/mounts; then
        echo "mount entry leaked for $1"
        return 1
    fi
    if grep -qE '[[:space:]]shfs[[:space:]]' /proc/mounts; then
        echo "shfs filesystem type leaked into /proc/mounts"
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------- 上游用例 U1/U2

# U1: shfsmount/shell-test.in —— 上游的 shell 能力探测
# 逐字执行上游脚本：19 个 POSIX 原语 type 检查（echo chgrp chmod chown cut dd df
# expr ln ls mkdir mv rm read rmdir tee test touch wc），全部命中才回 "ok stable"。
u1_shell_probe() {
    _out=$("$SH" "$RES/shell-test.in" 2>&1)
    if [ "$_out" != "ok stable" ]; then
        echo "shell-test.in replied: '$_out'"
        return 1
    fi
    return 0
}

# U2: shfsmount/perl-test.in —— 上游的 perl 能力探测
# 检查 perl 存在、版本 >= 5、Fcntl/IO::File/POSIX 模块可加载，再用 seteuid 试探
# 判断是否支持 preserve。root 下会额外回 " preserve"，非 root 只回 "ok stable"。
u2_perl_probe() {
    _out=$("$SH" "$RES/perl-test.in" 2>&1)
    case "$_out" in
        "ok stable"*) return 0 ;;
    esac
    echo "perl-test.in replied: '$_out'"
    return 1
}

# ---------------------------------------------------- 鸿蒙特有测试 H1（端到端）

# H1: 完整挂载流程消费者用例 —— 以本机 /bin/sh 顶替远端主机，跑通 shfs 协议握手。
# 构造输入: 空挂载点 + -t perl + -c "exec /bin/sh"（-n 不写 mtab）+ -vvv 全量跟踪
# 真实执行: 打包后的 bin/shfsmount，fork/exec 出平台 shell 作为远端，依次投递
#           上游 perl-test.in 探测脚本、546 行 perl-code.in 远端 helper、s_init 请求
# 产出结果: stderr 跟踪固定为 5 行关键输出（探测通过 → selected → 两次 ### 200）
# 校验内容: 上述 5 项逐条比对；进程必须恰好停在 mount(2)（鸿蒙 seccomp 拦截 mount
#           系统调用 → SIGSYS → shell 状态 159），且 /proc/mounts 无任何残留
h1_perl_handshake() {
    _mnt="$WORK/mnt-h1"
    mkdir -p "$_mnt" || return 1
    "$BIN/shfsmount" -t perl -c "exec $SH" -vvv -n "$_mnt" \
        >"$WORK/h1.out" 2>"$WORK/h1.err"
    _rc=$?

    grep -q '^Testing perl\.\.\. ok stable$' "$WORK/h1.err" || {
        echo "upstream perl probe never reported ok"
        sed 's/^/    /' "$WORK/h1.err"
        return 1
    }
    grep -q '^selected: perl$' "$WORK/h1.err" || {
        echo "protocol handshake did not select perl"
        sed 's/^/    /' "$WORK/h1.err"
        return 1
    }
    if [ "$(grep -c '^reply: ### 200$' "$WORK/h1.err")" -ne 2 ]; then
        echo "expected two ### 200 acks (helper load + s_init)"
        sed 's/^/    /' "$WORK/h1.err"
        return 1
    fi
    if [ "$_rc" -ne 159 ]; then
        echo "expected SIGSYS(159) at the mount(2) boundary, got $_rc"
        sed 's/^/    /' "$WORK/h1.err"
        return 1
    fi
    mount_untouched "$_mnt" || return 1
    return 0
}

# ---------------------------------------------------- 鸿蒙特有测试 H2（端到端）

# H2: 挂载选项装配 + 非 root 门禁消费者用例 —— 鸿蒙 PC 上适配以应用 uid（非 root）
# 运行，上游文档里的 root-only 行为在这里是日常路径，必须端到端验证。
# 构造输入: 空挂载点 + -o cachesize=4,ro（普通选项）与 -o uid=0（root-only 选项）
# 真实执行: bin/shfsmount 走完整 getopt/选项装配流程
# 产出结果: 前者把选项原样拼进 mount(2) 的 data 串并输出 options 跟踪行；后者在
#           建立连接之前就退出 2 并打印拒绝原因
# 校验内容: 跟踪行里逐字符出现 version=2,cachesize=4,ro 与 ,mnt=<挂载点>；
#           后者状态码恰为 2 且 stderr 恰为那句非 root 拒绝
h2_nonroot_option_gate() {
    _mnt="$WORK/mnt-h2"
    mkdir -p "$_mnt" || return 1

    "$BIN/shfsmount" -t perl -c "exec $SH" -v -n -o cachesize=4,ro "$_mnt" \
        >"$WORK/h2a.out" 2>"$WORK/h2a.err"
    grep -qF 'options: "version=2,cachesize=4,ro' "$WORK/h2a.err" || {
        echo "user mount options not assembled into the mount data string"
        sed 's/^/    /' "$WORK/h2a.err"
        return 1
    }
    grep -qF ",mnt=$_mnt" "$WORK/h2a.err" || {
        echo "mount point missing from the assembled options"
        return 1
    }

    "$BIN/shfsmount" -o uid=0 "$_mnt" >"$WORK/h2b.out" 2>"$WORK/h2b.err"
    _rc=$?
    if [ "$_rc" -ne 2 ]; then
        echo "root-only option: expected exit 2, got $_rc"
        return 1
    fi
    grep -qF "'uid=0' used by non-root user!" "$WORK/h2b.err" || {
        echo "root-only option rejected with an unexpected message"
        sed 's/^/    /' "$WORK/h2b.err"
        return 1
    }
    return 0
}

# ----------------------------------------------------------- CLI 契约用例 C1..C5

# C1: 配方把 SHFS_VERSION 显式传给 make（Makefile 默认从 Changelog 首行推导），
#     打包版本串必须烧进二进制
c1_version() {
    "$BIN/shfsmount" -V >"$WORK/c1.out" 2>"$WORK/c1.err" || return 1
    grep -qF 'shfsmount version 0.35(2)' "$WORK/c1.err" || {
        echo "version/protocol stamp wrong"
        sed 's/^/    /' "$WORK/c1.err"
        return 1
    }
    return 0
}

# C2: --help 走 usage(stdout) 且退出 0， getopt_long 表完整
c2_help() {
    "$BIN/shfsmount" --help >"$WORK/c2.out" 2>&1 || return 1
    grep -qFe '--cmd=COMMAND' "$WORK/c2.out" || return 1
    grep -qFe '--type=TYPE' "$WORK/c2.out" || return 1
    grep -qFe '--nomtab' "$WORK/c2.out" || return 1
    return 0
}

# C3: -t 指定未知协议时必须在建立连接前失败（不触发 mount(2)，不写 mtab）
c3_unknown_type() {
    _mnt="$WORK/mnt-c3"
    mkdir -p "$_mnt" || return 1
    "$BIN/shfsmount" -t nosuch -c "exec $SH" "$_mnt" \
        >"$WORK/c3.out" 2>&1
    _rc=$?
    [ "$_rc" -eq 2 ] || {
        echo "expected exit 2, got $_rc"
        sed 's/^/    /' "$WORK/c3.out"
        return 1
    }
    grep -qF 'Cannot create connection' "$WORK/c3.out" || return 1
    return 0
}

# C4: 挂载点不存在 → fullpath() 失败分支。上游这里把 argv[optind+1]（单参数时为
#     NULL）交给 %s，musl 打印 "(null)" 而不是崩溃；同时守住状态码 2、不得段错误
c4_invalid_mountpoint() {
    "$BIN/shfsmount" "$WORK/no-such-dir" >"$WORK/c4.out" 2>&1
    _rc=$?
    [ "$_rc" -eq 2 ] || {
        echo "expected exit 2 (not a crash), got $_rc"
        return 1
    }
    grep -qF 'Invalid path' "$WORK/c4.out" || return 1
    return 0
}

# C5: shfsumount 三个入口 —— 无参 usage(1)、-v 版本(0)、非 shfs 目录被 statfs
#     魔数守卫拒识（EINVAL, 1），且不会走到 umount(2)/mtab 重写
c5_umount_contract() {
    "$BIN/shfsumount" >"$WORK/c5a.out" 2>&1
    _rc=$?
    [ "$_rc" -eq 1 ] || {
        echo "no-arg usage: expected exit 1, got $_rc"
        return 1
    }
    grep -qF 'Usage: shfsumount mount_point' "$WORK/c5a.out" || return 1

    "$BIN/shfsumount" -v >"$WORK/c5b.out" 2>&1
    _rc=$?
    [ "$_rc" -eq 0 ] || {
        echo "-v: expected exit 0, got $_rc"
        return 1
    }
    grep -qF 'shfsumount version 0.35(2)' "$WORK/c5b.out" || return 1

    _mnt="$WORK/mnt-c5"
    mkdir -p "$_mnt" || return 1
    "$BIN/shfsumount" "$_mnt" >"$WORK/c5c.out" 2>&1
    _rc=$?
    [ "$_rc" -eq 1 ] || {
        echo "non-shfs dir: expected exit 1, got $_rc"
        return 1
    }
    grep -qF 'Invalid argument' "$WORK/c5c.out" || return 1
    return 0
}

expect U1-shell-test.in        u1_shell_probe
expect U2-perl-test.in         u2_perl_probe
expect H1-ohos-perl-handshake  h1_perl_handshake
expect H2-ohos-nonroot-gate    h2_nonroot_option_gate
expect C1-version              c1_version
expect C2-help                 c2_help
expect C3-unknown-type         c3_unknown_type
expect C4-invalid-mountpoint   c4_invalid_mountpoint
expect C5-umount-contract      c5_umount_contract

printf '\n%d cases run, %d failed\n' "$CASES" "$FAILED"
if [ "$CASES" -ne 9 ]; then
    echo "case count drifted away from the declared 9"
    exit 1
fi
[ "$FAILED" -eq 0 ] || exit 1
echo "OK: shfs 0.35 OHOS suite passed (9/9)"
