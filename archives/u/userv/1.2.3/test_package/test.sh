#!/bin/sh
# test_package/test.sh — userv 1.2.3 打包产物验证（R34：实质依赖被测产物，不是空壳）
#
# 平台事实（本脚本的分层依据，均有真机/源码证据，见 ../notes.md §十）：
#   * `uservd`（守护进程）可以真正执行：overlord.c:279-283 在 openlog/chdir 之前校验参数，
#     带参数时打印 `usage: uservd [-daemon]` 到 stderr 并以 3 退出 —— 不需要 root，可稳定断言。
#   * `userv`（客户端）**按设计要求以 setuid root 安装**：client.c:808-821 的 security_init()
#     在解析参数之前就调用 priv_suspend()，后者无条件执行
#         setreuid(0, myuid)      // client.c:248
#     Conan 包内的二进制不是 setuid root（CI 用户无法 chown root），因此：
#       - 在普通 Linux 上：该调用返回 EPERM，客户端报错并以非 0 退出；
#       - 在 OHOS 真机上：该特权系统调用被安全策略拦截，进程直接被 SIGSYS 杀死
#         （shell 报 exit=159 / "Bad system call"；已用最小 C 探针复现，notes.md §10.5）。
#     所以本脚本不会把"跑不了 userv"伪装成通过：能跑就跑完整 CLI 契约；
#     跑不了就改为对**打包二进制本身**做构建身份校验（版本串/用法串/许可证串 + ELF 头），
#     并显式打印 SKIP 与原因。这两条路径都要求 bin/ 下的真实产物存在，
#     因此 CI L1e（移走 bin/ 后测试必须失败）依然成立。
#
# 用法: bash test.sh <package_bin_dir>
# 只用 POSIX 语法（不依赖 bash 的 pipefail），CONFIG_SHELL 缺失时用 sh 也能跑。
set -eu

BIN_DIR="${1:?usage: test.sh <package_bin_dir>}"
USERV="$BIN_DIR/userv"
USERVD="$BIN_DIR/uservd"
EXPECTED_VERSION="1.2.3std"

checks=0
failures=0
skips=0

ok() {
    checks=$((checks + 1))
    echo "[test] PASS: $*"
}

bad() {
    checks=$((checks + 1))
    failures=$((failures + 1))
    echo "[test] FAIL: $*" >&2
}

skip() {
    skips=$((skips + 1))
    echo "[test] SKIP: $*"
}

has_string() { # has_string <file> <needle>
    grep -a -q -F -- "$2" "$1" 2>/dev/null
}

is_aarch64_elf() { # is_aarch64_elf <file>  — ELF magic + 64-bit LSB + e_machine=0xB7 (AArch64)
    hex=$(head -c 20 "$1" 2>/dev/null | od -An -tx1 | tr -d ' \n')
    case "$hex" in
        7f454c4602*b700) return 0 ;;
        *) return 1 ;;
    esac
}

echo "[test] userv 1.2.3 packaged-artifact verification (bin dir: $BIN_DIR)"
echo "[test] platform: $(uname -s) $(uname -m)"

# ── 1/2. 打包产物存在且可执行（L1e：移走 bin/ 后这里必然失败）──
for name in userv uservd; do
    path="$BIN_DIR/$name"
    if [ -x "$path" ]; then
        ok "$name exists and is executable"
    else
        bad "$name missing or not executable: $path"
    fi
done
[ -x "$USERV" ] && [ -x "$USERVD" ] || { echo "[test] fatal: artifacts missing"; exit 1; }

# ── 3/4. 产物是 aarch64 ELF（ELF magic + e_machine=0xB7）──
for name in userv uservd; do
    if is_aarch64_elf "$BIN_DIR/$name"; then
        ok "$name is an AArch64 ELF"
    else
        bad "$name is not an AArch64 ELF"
    fi
done

# ── 5/6. uservd 真实执行：参数校验（overlord.c:279-283），不需要 root ──
rc=0
daemon_out="$("$USERVD" --help 2>&1)" || rc=$?
if [ "$rc" -eq 3 ]; then
    ok "uservd rejects unexpected arguments with exit status 3"
else
    bad "uservd --help exit=$rc (expected 3 per overlord.c:283)"
fi
case "$daemon_out" in
    *"usage: uservd [-daemon]"*)
        ok "uservd prints its usage line" ;;
    *)
        bad "uservd usage line missing (got: $daemon_out)" ;;
esac

# ── 7+. userv 客户端：能跑就跑完整 CLI 契约；不能跑就退化为二进制契约校验 ──
rc=0
version_out="$("$USERV" --version 2>&1)" || rc=$?
if [ "$rc" -eq 0 ] && [ "$version_out" = "$EXPECTED_VERSION" ]; then
    ok "userv --version == '$EXPECTED_VERSION' (exit 0)"

    rc=0
    help_out="$("$USERV" --help 2>&1)" || rc=$?
    [ "$rc" -eq 0 ] && ok "userv --help exits 0" || bad "userv --help exited $rc"
    case "$help_out" in
        *"usage: userv <options>"*) ok "userv --help prints the usage contract" ;;
        *) bad "userv --help missing usage contract" ;;
    esac
    case "$help_out" in
        *"userv and uservd version $EXPECTED_VERSION."*) ok "userv --help prints the version line" ;;
        *) bad "userv --help missing version line" ;;
    esac

    rc=0
    copy_out="$("$USERV" --copyright 2>&1)" || rc=$?
    case "$copy_out" in
        *"GNU General Public License"*) ok "userv --copyright prints the GPLv3 notice" ;;
        *) bad "userv --copyright output unexpected (exit=$rc)" ;;
    esac

    rc=0
    err_out="$("$USERV" --definitely-not-a-userv-option 2>&1 >/dev/null)" || rc=$?
    [ "$rc" -ne 0 ] && ok "userv rejects an unknown option (exit $rc)" \
                    || bad "userv accepted an unknown option"
    case "$err_out" in
        *"usage: userv"*) ok "userv prints usage to stderr on a bad option" ;;
        *) bad "no usage text on stderr for a bad option" ;;
    esac
else
    # 客户端需要 setuid-root；在 CI 沙箱里跑不起来（OHOS 上表现为 SIGSYS/exit 159）
    skip "userv runtime CLI contract (exit=$rc): client.c:248 setreuid(0,uid) requires setuid-root install; OHOS traps the syscall (SIGSYS)"
    if has_string "$USERV" "$EXPECTED_VERSION"; then
        ok "userv embeds the build version string '$EXPECTED_VERSION' (static build identity)"
    else
        bad "userv does not embed '$EXPECTED_VERSION'"
    fi
    if has_string "$USERV" "usage: userv"; then
        ok "userv embeds its usage contract text"
    else
        bad "userv does not embed its usage contract text"
    fi
    if has_string "$USERV" "GNU General Public License"; then
        ok "userv embeds the GPLv3 notice"
    else
        bad "userv does not embed the GPLv3 notice"
    fi
fi

echo "[test] assertions: $checks, failures: $failures, skipped: $skips"
if [ "$failures" -ne 0 ]; then
    echo "[test] userv 1.2.3 packaged-artifact verification FAILED" >&2
    exit 1
fi
echo "[test] userv 1.2.3 packaged-artifact verification OK"
