#!/bin/sh
# test_package/test.sh — zerolang 0.3.4 消费者功能测试
#
# 参数 $1 = 打包后的 `zero` 编译器绝对路径（由 test_package/conanfile.py 传入，
# 不做脆弱的 `command -v zero` PATH 查找）。
# 参数 $2 = 可写且可执行（exec-capable）的工作目录（由 conanfile.py 传入
# conan-home 包目录父级下的 test_package_run/）。执行 `zero run` 会把编译/链接
# 产物写到 <work>/.zero/out/ 并经 execv 直接执行。
#
# OHOS 端口差异（关键）：`zero run` 默认走 direct 后端，它不经 clang，而是用
# emit_elf_aarch64.c 的 z_elf_write_executable64 直接写一个静态、绝对寻址的
# ET_EXEC 镜像（e_type=2，固定 base_addr=0x400000，单 RX PT_LOAD，无 interpreter）。
# HarmonyOS（Linux 内核，实行 PIE/位置无关执行策略，类 Android）以 EACCES 拒绝
# execve 这种非 PIE/ET_EXEC 镜像 → `zero run` rc=127 "Permission denied"。此与
# 承载目录是否 noexec、工作目录放哪（TMPDIR / test_package 源目录 / conan-home
# 三处实测全部 EACCES）无关；配方里 smoke/zero 本体是 clang 默认 PIE(ET_DYN)，
# 在同一 conan-home 子树执行正常，故同样排除挂载因素。
#
# 修复：run 显式选 `--backend llvm`。LLVM 后端把 zero 源码 → LLVM IR → 经
# /data/service/hnp/bin/clang 编译 zero_runtime.c 并链接（配方 _patch_no_pie 已把
# 该路径的 "-no-pie" 改为 "-pie"），产出 clang 链接的 PIE/ET_DYN 可执行，与
# smoke/zero 同为 OHOS 内核接受的形态，hello-world 便能真正 exec 输出 "hello"。
# （x86_64 实证：direct 产物 readelf Type=EXEC 341B；llvm+pie 产物 Type=DYN 35K 且
# 运行输出 hello。断言内容不变，仅切换编译器自带的后端以适配 OHOS 执行策略。）
#
# 驱动 `zero` 执行两个真实断言：
#   1. `zero --version` 输出包含 "0.3.4"（Homebrew 同款冒烟）
#   2. hello-world 源经 `zero check` 通过、`zero run --backend llvm` 输出期望内容
#      （README/Homebrew 同款流程，仅以 llvm 后端产出 OHOS 可执行的 PIE）
#
# 只有两个断言全部真正通过才打印 HMBS_TEST_PACKAGE_RESULT；任一失败以非零
# 退出并打印诊断（run 失败时额外回显 zero run 的 stdout/stderr，便于定位具体 errno）。
set -u

ZERO="${1:-}"
WORK_DIR="${2:-}"
if [ -z "$ZERO" ] || [ ! -e "$ZERO" ]; then
    echo "consumer test FAILED: zero binary not found at '${ZERO}'" >&2
    exit 1
fi

# 工作目录：优先用显式传入的 exec-capable 目录（conan-home 下），缺失/不可写时
# 退回当前 cwd（conanfile 已将 cwd 设为同一 conan-home exec 目录）。
if [ -z "$WORK_DIR" ] || [ ! -d "$WORK_DIR" ] || [ ! -w "$WORK_DIR" ]; then
    WORK_DIR="$(pwd)"
fi
TP_DIR="$(mktemp -d "$WORK_DIR/zero-tp-XXXXXX")" || { echo "mktemp failed"; exit 1; }
trap 'rm -rf "$TP_DIR"' EXIT

# ---- 断言 1: 版本 ----
VER_OUT="$("$ZERO" --version 2>&1)" || { echo "consumer test FAILED: zero --version rc=$?" >&2; exit 1; }
echo "zero --version -> $VER_OUT"

# ---- 断言 2: hello-world check + run ----
mkdir -p "$TP_DIR/src"
cat > "$TP_DIR/src/main.0" <<'SRC'
pub fn main(world: World) -> Void raises {
  check world.out.write("hello")
}
SRC
( cd "$TP_DIR" && "$ZERO" init >/dev/null 2>&1 ) || { echo "consumer test FAILED: zero init" >&2; exit 1; }
( cd "$TP_DIR" && "$ZERO" import >/dev/null 2>&1 ) || { echo "consumer test FAILED: zero import" >&2; exit 1; }
( cd "$TP_DIR" && "$ZERO" check >/dev/null 2>&1 ) || { echo "consumer test FAILED: zero check" >&2; exit 1; }
RUN_OUT="$(cd "$TP_DIR" && "$ZERO" run --backend llvm 2>&1)" || { echo "consumer test FAILED: zero run rc=$?" >&2; echo "--- zero run output ---" >&2; echo "$RUN_OUT" >&2; echo "--- end ---" >&2; exit 1; }
echo "hello-world run output -> $RUN_OUT"

passed_count=0
[ "${VER_OUT#*0.3.4}" != "$VER_OUT" ] && passed_count=$((passed_count + 1)) \
    || echo "assert-1 FAILED: version does not contain 0.3.4"
[ "$RUN_OUT" = "hello" ] && passed_count=$((passed_count + 1)) \
    || echo "assert-2 FAILED: hello-world run output != 'hello'"

echo "test_package assertions passed: $passed_count/2"
if [ "$passed_count" -eq 2 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"$ZERO (--version + hello-world run)\",\"discovered\":2,\"passedCount\":2}"
    exit 0
fi
echo "consumer test FAILED: ${passed_count}/2 assertions passed" >&2
exit 1
