#!/bin/sh
# musl-nscd 消费者端到端测试（POSIX shell，见 test_package/conanfile.py）
#
# 真实链路：
#   编译期 桩 NSS 模块 libnss_ohostest.so.2（#include 被测包的 <nss.h>）
#          协议客户端 nscd_client
#   运行期 写 nsswitch.conf → 启动被测 nscd（-c/-s/-p 全部改道到临时目录）
#          → 客户端经 AF_UNIX socket 用 NSCD 二进制协议取回条目 → 校验字段
#
# ── OHOS 平台约束（实测，见 MANIFEST.yml platform_exemptions）──
#   OHOS 安全策略（hmmac/SELinux）只允许在应用沙箱数据目录下 bind() AF_UNIX
#   文件系统 socket；在 $HOME / $TMPDIR / 仓库目录下 bind() 一律返回 EPERM。
#   因此本脚本按候选目录顺序探测可 bind 的位置；若全部不可用，则不伪造通过，
#   而是把端到端协议组标记为平台豁免（不计入 PASS），并断言守护进程确实越过了
#   配置解析与 NSS 模块 dlopen、仅因 bind 被拒而退出。
#
# 环境变量（由 test_package/conanfile.py 注入）：
#   NSCD_BIN        被测包安装出的 nscd 可执行文件绝对路径
#   TEST_BIN_DIR    桩 NSS 模块与协议客户端所在目录（同时作为 LD_LIBRARY_PATH）
#   NSCD_SOCK_DIR   可选，指定优先尝试的 socket 目录

# ⚠️ 刻意不启用 `set -e`：断言失败后仍需继续跑完全部用例并累计 PASS/FAIL，
#    而不是首错即退（否则顶层无法给出"哪几条失败"的完整清单）。
#    `set -o pipefail` 非 POSIX，仅在 bash 下启用（conanfile.py 优先用 bash 调用）。
set -u
if [ -n "${BASH_VERSION:-}" ]; then
	set -o pipefail
fi

NSCD_BIN="${NSCD_BIN:?缺少 NSCD_BIN}"
TEST_BIN_DIR="${TEST_BIN_DIR:?缺少 TEST_BIN_DIR}"

PASS=0
FAIL=0
E2E_SKIPPED=0
OFFLINE=0

pass() {
	PASS=$((PASS + 1))
	printf '  [PASS] %s\n' "$1"
}

fail() {
	FAIL=$((FAIL + 1))
	printf '  [FAIL] %s\n' "$1"
}

skip() {
	printf '  [SKIP] %s\n' "$1"
}

expect_eq() {
	# $1=用例名 $2=实际值 $3=期望值
	if [ "$2" = "$3" ]; then
		pass "$1"
	else
		fail "$1（期望 [$3]，实际 [$2]）"
	fi
}

expect_match() {
	# $1=用例名 $2=文件 $3=ERE 模式
	if grep -q -E -- "$3" "$2" 2>/dev/null; then
		pass "$1"
	else
		fail "$1（$2 中未匹配 [$3]）"
	fi
}

WORK="${TMPDIR:-/tmp}/musl-nscd-e2e-$$"
rm -rf "$WORK"
mkdir -p "$WORK" || {
	echo "无法创建临时目录 $WORK"
	exit 1
}

NSCD_PID=""
SOCK_DIR=""
SOCK=""
LAST_ERR=""

cleanup() {
	if [ -n "$NSCD_PID" ]; then
		kill "$NSCD_PID" 2>/dev/null
		wait "$NSCD_PID" 2>/dev/null
	fi
	[ -n "$SOCK_DIR" ] && rm -rf "$SOCK_DIR"
	rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

CONF="$WORK/nsswitch.conf"
PIDFILE="$WORK/nscd.pid"
CLIENT="$TEST_BIN_DIR/nscd_client"

# SOCK 候选目录：应用沙箱数据目录（OHOS 唯一允许 bind AF_UNIX 的位置）优先
SOCK_CANDIDATES="${NSCD_SOCK_DIR:-} /data/storage/el2/base ${TMPDIR:-/tmp}"

echo "== musl-nscd 消费者端到端测试 =="
echo "   nscd     : $NSCD_BIN"
echo "   测试辅助 : $CLIENT"
echo "   工作目录 : $WORK"

# ── 1. 产物存在性（L1e 反向验证依赖点：移除包后本项必然失败）──
if [ -x "$NSCD_BIN" ]; then
	pass "被测包安装出可执行守护进程 sbin/nscd"
else
	fail "未找到可执行文件 $NSCD_BIN"
	echo "结果: PASS=$PASS FAIL=$FAIL"
	exit 1
fi

# ── 2. 错误路径：配置文件缺失必须报错退出（die_fmt 真实代码路径）──
"$NSCD_BIN" -c "$WORK/absent.conf" >"$WORK/out.absent" 2>&1
expect_eq "配置文件缺失时以 1 退出" "$?" "1"
expect_match "配置文件缺失时给出明确原因" "$WORK/out.absent" "was not found"

# ── 3. 错误路径：nsswitch.conf 中的 merge 动作上游不支持，必须被拒绝 ──
cat >"$WORK/merge.conf" <<'EOF'
passwd: ohostest [SUCCESS=merge]
EOF
"$NSCD_BIN" -c "$WORK/merge.conf" >"$WORK/out.merge" 2>&1
expect_eq "nsswitch.conf 的 merge 动作被拒绝" "$?" "1"
expect_match "merge 被拒绝时给出说明" "$WORK/out.merge" "merge action"

# ── 4. 合法 nsswitch.conf：解析 + NSS 模块 dlopen + AF_UNIX bind ──
cat >"$CONF" <<'EOF'
passwd: ohostest
group:  ohostest
EOF

start_daemon() {
	# $1 = socket 所在目录；成功返回 0 并设置 NSCD_PID / SOCK / SOCK_DIR
	SOCK_DIR="$1"
	mkdir -p "$SOCK_DIR" 2>/dev/null || return 1
	SOCK="$SOCK_DIR/nscd.sock"
	rm -f "$SOCK" "$PIDFILE"

	LD_LIBRARY_PATH="$TEST_BIN_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
		"$NSCD_BIN" -c "$CONF" -s "$SOCK" -p "$PIDFILE" >"$WORK/out.daemon" 2>&1 &
	NSCD_PID=$!

	i=0
	while [ "$i" -lt 50 ]; do
		[ -S "$SOCK" ] && return 0
		kill -0 "$NSCD_PID" 2>/dev/null || return 1
		i=$((i + 1))
		sleep 0.1
	done
	return 1
}

for cand in $SOCK_CANDIDATES; do
	[ -n "$cand" ] || continue
	if start_daemon "$cand/musl-nscd-e2e-$$"; then
		break
	fi
	LAST_ERR="$(cat "$WORK/out.daemon" 2>/dev/null)"
	kill "$NSCD_PID" 2>/dev/null
	wait "$NSCD_PID" 2>/dev/null
	NSCD_PID=""
	SOCK=""
	SOCK_DIR=""
done

if [ -n "$SOCK" ]; then
	pass "守护进程绑定并监听 AF_UNIX socket（dlopen 桩 NSS 模块成功）[$SOCK_DIR]"
	expect_eq "守护进程写出的 pid 与监听进程一致" "$(cat "$PIDFILE" 2>/dev/null)" "$NSCD_PID"
else
	OFFLINE=1
	# 平台豁免路径：仍须断言守护进程越过了配置解析与 NSS 模块 dlopen，
	# 失败点正是被安全策略拒绝的 AF_UNIX bind()（而非解析/加载失败）。
	case "$LAST_ERR" in
	*"Operation not permitted"*)
		pass "守护进程越过配置解析与 NSS 模块 dlopen，仅因平台拒绝 AF_UNIX bind 而退出"
		;;
	*)
		fail "守护进程非预期失败（预期为 bind 的 EPERM）：[$LAST_ERR]"
		;;
	esac
	skip "端到端协议组未执行：本环境不允许在应用沙箱目录外 bind AF_UNIX socket"
	E2E_SKIPPED=1
fi

# ── 5. 端到端协议组（仅在 socket 可用时执行）──
if [ "$OFFLINE" = 0 ]; then
	# GETPWBYNAME
	"$CLIENT" "$SOCK" pw-name ohostest-user >"$WORK/r.pwname" 2>&1
	expect_eq "GETPWBYNAME 协议往返成功" "$?" "0"
	expect_match "GETPWBYNAME 返回 FOUND" "$WORK/r.pwname" "^FOUND$"
	expect_match "GETPWBYNAME 返回用户名" "$WORK/r.pwname" "^name=ohostest-user$"
	expect_match "GETPWBYNAME 返回 uid" "$WORK/r.pwname" "^uid=4242$"
	expect_match "GETPWBYNAME 返回 gid" "$WORK/r.pwname" "^gid=4242$"
	expect_match "GETPWBYNAME 返回口令字段" "$WORK/r.pwname" "^passwd=x$"
	expect_match "GETPWBYNAME 返回 gecos" "$WORK/r.pwname" "^gecos=OHOS NSS stub$"
	expect_match "GETPWBYNAME 返回家目录" "$WORK/r.pwname" "^dir=/home/ohostest-user$"
	expect_match "GETPWBYNAME 返回 shell" "$WORK/r.pwname" "^shell=/bin/sh$"

	# GETPWBYNAME 未命中
	"$CLIENT" "$SOCK" pw-name nobody >"$WORK/r.pwmiss" 2>&1
	expect_eq "未命中用户名的请求仍正常往返" "$?" "0"
	expect_match "未命中用户名返回 NOTFOUND" "$WORK/r.pwmiss" "^NOTFOUND$"

	# GETPWBYUID（十进制字符串 key 解析路径）
	"$CLIENT" "$SOCK" pw-uid 4242 >"$WORK/r.pwuid" 2>&1
	expect_eq "GETPWBYUID 协议往返成功" "$?" "0"
	expect_match "GETPWBYUID 返回用户名" "$WORK/r.pwuid" "^name=ohostest-user$"
	expect_match "GETPWBYUID 返回 uid" "$WORK/r.pwuid" "^uid=4242$"

	# GETGRBYNAME
	"$CLIENT" "$SOCK" gr-name ohostest-group >"$WORK/r.grname" 2>&1
	expect_eq "GETGRBYNAME 协议往返成功" "$?" "0"
	expect_match "GETGRBYNAME 返回 FOUND" "$WORK/r.grname" "^FOUND$"
	expect_match "GETGRBYNAME 返回组名" "$WORK/r.grname" "^name=ohostest-group$"
	expect_match "GETGRBYNAME 返回 gid" "$WORK/r.grname" "^gid=4242$"
	expect_match "GETGRBYNAME 返回成员数" "$WORK/r.grname" "^nmembers=1$"
	expect_match "GETGRBYNAME 返回成员" "$WORK/r.grname" "^member=ohostest-user$"

	# GETGRBYGID + 未命中
	"$CLIENT" "$SOCK" gr-gid 4242 >"$WORK/r.grgid" 2>&1
	expect_eq "GETGRBYGID 协议往返成功" "$?" "0"
	expect_match "GETGRBYGID 返回组名" "$WORK/r.grgid" "^name=ohostest-group$"

	"$CLIENT" "$SOCK" gr-name no-such-group >"$WORK/r.grmiss" 2>&1
	expect_eq "未命中组名的请求仍正常往返" "$?" "0"
	expect_match "未命中组名返回 NOTFOUND" "$WORK/r.grmiss" "^NOTFOUND$"

	# 反复连接：服务端线程池复用
	rounds=0
	ok=0
	while [ "$rounds" -lt 8 ]; do
		out=$("$CLIENT" "$SOCK" pw-name ohostest-user 2>&1)
		echo "$out" | grep -q "^uid=4242$" && ok=$((ok + 1))
		rounds=$((rounds + 1))
	done
	expect_eq "连续 8 次请求全部成功" "$ok" "8"
fi

echo
if [ "$E2E_SKIPPED" = 1 ]; then
	echo "结果: PASS=$PASS FAIL=$FAIL SKIP=端到端协议组（平台豁免，见 MANIFEST.yml）"
else
	echo "结果: PASS=$PASS FAIL=$FAIL SKIP=0"
fi
if [ "$FAIL" -ne 0 ]; then
	exit 1
fi
exit 0
