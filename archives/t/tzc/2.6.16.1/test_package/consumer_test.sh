#!/bin/sh
# tzc 2.6.16.1 —— 消费者端到端用例（HarmonyOS PC / aarch64）
#
# 用法: consumer_test.sh <bindir>
#
# 背景：tzc 是 Project Athena Zephyr 通知服务客户端，完整业务需要活的 Zephyr
# HostManager 网络服务；CI 环境无该服务，无法构造「订阅并收到 zgram」的完整
# 业务闭环。因此按「CLI + 外部服务不可达」范式做**真实可执行性**验证：原生真实
# 执行被测二进制，本机动态加载器必须完整解析并加载整个 DT_NEEDED 闭包（含传递
# 依赖与重定位）才能进入 main()，随后上游源码语义（say_hi 版本横幅 + 经 libzephyr
# 的 ZInitialize() 走真实业务 API 并以 EXIT_FAILURE 退出）即为「闭包在本机真实
# 加载且依赖满足」的直接证据。全部判定基于命令退出码与原始输出，不使用 Python
# assert，也不做字符串静态校验式的空壳断言。
#
# 设计约束（对照 xsct 2.3，PR #15143 build #80198 实证）：**不做**宿主 python
# ctypes dlopen —— HNP 安装的 python3（CI worker 宿主）运行在受限 linker
# namespace 中，对缓存路径下的共享库 dlopen 会得到 EACCES(Permission denied)，
# 而 exec 时按 DT_NEEDED 加载不受此限，会导致本地绿、CI 红。「闭包真实加载」
# 一律由 B 节原生执行承担。
#
# 覆盖两部分：
#
#  A. HarmonyOS 专有非断言检查（静态）
#     A1 tzc 必须是 OHOS aarch64 原生 ELF 可执行文件
#     A2 tzc 的 DT_NEEDED 动态依赖闭包必须含 libzephyr.so.4（并打印闭包清单）
#     A3 com_err 必须是**已定义**符号 —— e2fsprogs 的 libcom_err.a 静态链入证据
#
#  B. 端到端消费者用例（原生进程真实执行 + 上游语义校验）
#     B1 `tzc -o`：真实运行到 setup()，调用 libzephyr 的 ZInitialize()/ZOpenPort()，
#        无 HostManager 时按上游语义经 com_err 钩子输出 elisp 错误并优雅返回
#        EXIT_FAILURE(1)
#     B2 `tzc --bogus`：真实走上游 getopt/usage 路径，usage() 后 bail(1)
#
# 参数: $1 = 被测包 bin 目录（含 tzc）
set -u

fail() { echo "FAIL: $*" >&2; exit 1; }

BINDIR="$1"
TZC="$BINDIR/tzc"

[ -x "$TZC" ] || fail "缺少可执行文件 $TZC"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/tzc-consumer.XXXXXX" 2>/dev/null || mktemp -d 2>/dev/null) \
  || fail "无法创建临时目录 (mktemp)"
trap 'rm -rf "$TMP" >/dev/null 2>&1 || true' EXIT INT TERM

# 如环境提供超时工具则加超时，避免上游进入事件循环时挂死
if command -v timeout >/dev/null 2>&1; then
  LIMIT="timeout 30"
elif [ -x /bin/timeout ]; then
  LIMIT="/bin/timeout 30"
else
  LIMIT=""
fi

# ─────────────────────── A. HarmonyOS 专有非断言检查 ───────────────────────
echo "== A. HarmonyOS 专有非断言检查：原生 ELF 与动态依赖闭包 =="

echo "+ readelf -h $TZC"
readelf -h "$TZC"
readelf -h "$TZC" | grep -q 'ELF' || fail "A1: tzc 不是 ELF 可执行文件"
readelf -h "$TZC" | grep -q 'AArch64' || fail "A1: tzc 不是 aarch64 原生 ELF 可执行文件"

echo "+ readelf -d $TZC"
readelf -d "$TZC"
readelf -d "$TZC" | grep -q 'NEEDED' || fail "A2: tzc 无 DT_NEEDED 动态依赖闭包"
readelf -d "$TZC" | grep -q 'libzephyr.so.4' || fail "A2: tzc 闭包缺 libzephyr.so.4"

echo "+ DT_NEEDED 闭包清单"
readelf -d "$TZC" | sed -n 's/.*(NEEDED).*\[\(.*\)\]/  \1/p'

echo "+ readelf -sW $TZC | grep com_err（静态链入证据）"
comerr_addr=$(readelf -sW "$TZC" | awk '/ com_err$/ && $7 != "UND" {print $2; exit}')
[ -n "$comerr_addr" ] || fail "A3: com_err 未在 tzc 内静态定义（libcom_err.a 未静态链入）"
readelf -sW "$TZC" | grep -E ' com_err$' | sed 's/^/  /'
echo "  -> com_err 已定义 @ 0x$comerr_addr（非 UND，证明静态链入）"

echo "OK A: tzc 为 aarch64 原生 ELF；DT_NEEDED 闭包声明完整；com_err 静态链入"

# ───────────────────────── B. 端到端消费者用例 ─────────────────────────
echo "== B. 消费者端到端用例：真实执行 tzc（原生进程） =="

# B1: 真实执行到 setup()，经 libzephyr ZInitialize / ZOpenPort 走业务 API。
#     无 HostManager 时上游按源码语义输出 elisp 错误并 EXIT_FAILURE(1)；
#     若闭包缺失，加载器会以 127 退出并输出 shared library 错误。
( $LIMIT "$TZC" -o </dev/null >"$TMP/b1.out" 2>"$TMP/b1.err" )
rc=$?
echo "+ $TZC -o (no HostManager) -> exit=$rc"
sed 's/^/    /' "$TMP/b1.out" 2>/dev/null || true
[ "$rc" -ne 127 ] || fail "B1: 动态加载器报告共享库缺失（exit=127）"
[ "$rc" -ne 126 ] || fail "B1: tzc 不可执行（exit=126）"
[ "$rc" -ne 124 ] || fail "B1: tzc 未在超时内退出（疑似进入事件循环）"
grep -qi 'shared library' "$TMP/b1.err" && fail "B1: 存在共享库加载错误"
grep -q '; Version 2.6.16' "$TMP/b1.out" || fail "B1: 未见上游 say_hi 版本横幅（未真实执行上游代码）"
grep -q 'Hostmanager not responding' "$TMP/b1.out" || fail "B1: 未见 libzephyr 业务 API 失败证据（ZInitialize 未被执行）"
grep -q '(tzcspew . error)' "$TMP/b1.out" || fail "B1: 未见上游 elisp 错误协议输出"
[ "$rc" -eq 1 ] || fail "B1: 期望上游 EXIT_FAILURE(1)，实际 exit=$rc"

# B2: 真实走上游 getopt/usage 路径（非法选项 -> usage() -> bail(1)）
( $LIMIT "$TZC" --bogus </dev/null >"$TMP/b2.out" 2>"$TMP/b2.err" )
rc2=$?
echo "+ $TZC --bogus -> exit=$rc2"
sed 's/^/    /' "$TMP/b2.err" 2>/dev/null || true
[ "$rc2" -ne 127 ] || fail "B2: 动态加载器报告共享库缺失（exit=127）"
[ "$rc2" -ne 126 ] || fail "B2: tzc 不可执行（exit=126）"
[ "$rc2" -ne 124 ] || fail "B2: tzc 未在超时内退出"
grep -qi 'shared library' "$TMP/b2.err" && fail "B2: 存在共享库加载错误"
grep -q 'usage: tzc \[options\]' "$TMP/b2.err" || fail "B2: 未见上游 usage() 输出"
grep -q '; Version 2.6.16' "$TMP/b2.out" || fail "B2: 未见上游 say_hi 版本横幅"
[ "$rc2" -eq 1 ] || fail "B2: 期望上游 usage()+bail(1)，实际 exit=$rc2"

echo "OK B: tzc 真实执行，DT_NEEDED 闭包经本机加载器完整解析加载，上游语义符合预期"
echo "ALL CONSUMER TESTS PASSED"
