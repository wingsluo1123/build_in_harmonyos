#!/bin/sh
# test_ohos — tup 0.8 HarmonyOS PC 专项验证（自包含，可在真机单独执行）
#
# 面向「已安装的 tup 0.8 包」，在真实鸿蒙 PC（aarch64 / OHOS, musl + Linux ABI,
# toybox 用户态, /tmp 为只读 erofs 挂载）上做端到端消费者验证。与上游自带套件
# （test/，981 项）和 test_package 冒烟测试的分工：
#
#   * 上游套件验证 tup 自身行为，跑在构建树里；
#   * 本脚本验证「装出来的包」在真机上的可用性，逐条对应本次适配的改动：
#
#   T1  CLI 与后端：tup --version（TUP_LABEL）与 tup server == ldpreload
#       （平台无可用 /dev/fuse，build.sh 的 HarmonyOS 分支必须选 ldpreload）
#   T2  端到端真实构建（完整消费者用例）：用 Tupfile 编译并链接一个 C 程序，
#       运行产物核验输出 → 未变更时二次执行不重建 → 改动源码后增量重建
#   T3  toybox `touch` 写事件追踪（补丁 0002）：新建输出的 O_CREAT 路径与
#       输出已存在时的 utimensat 路径都必须被记为写事件，否则 tup 报
#       "Expected to write to file ... but didn't"。
#       注：tup 只把「命令真正访问过」的文件纳入重跑判据（ldpreload 后端按实际
#       open/stat 访问建依赖），所以重跑用例让命令显式读取 %f，否则输入变更
#       不会触发重跑（这与写事件追踪无关，是 tup 的既有设计）。
#   T4  只读 /tmp 上的 tmpfile 回退（补丁 0005–0008）：回退链为
#       $TMPDIR → 项目内 .tup/tmp → /tmp，三条路径下都不得出现
#       `tmpfile: Permission denied`（平台 /tmp 是只读 erofs 挂载）
#   T5  TMPDIR 随默认环境白名单传入构建命令（补丁 0004）
#   T6  产物平台一致性：bin/tup 为 aarch64 ELF、注入库与可执行文件同目录、
#       无宿主构建路径（/storage、/home、/Users）泄漏
#
# 用法：bash run_ohos_test.sh [已安装包目录（含 tup 与 tup-ldpreload.so）]
#       省略目录时取 PATH 上的 tup。退出码 0 = 全部通过。
set -u

BINDIR="${1:-}"
if [ -n "$BINDIR" ]; then
	TUP="$BINDIR/tup"
else
	TUP="$(command -v tup 2>/dev/null || true)"
	[ -n "$TUP" ] || { echo "FAIL: PATH 上找不到 tup，请传入已安装包目录"; exit 2; }
	BINDIR="$(dirname "$TUP")"
fi
[ -x "$TUP" ] || { echo "FAIL: $TUP 不存在或不可执行"; exit 2; }

# 工作目录必须落在可写位置（鸿蒙 /tmp 是只读 erofs 挂载）
TMPROOT="${TMPDIR:-$HOME/tmp}"
case "$TMPROOT" in /tmp|/tmp/*) TMPROOT="$HOME/tmp";; esac
WORK="$TMPROOT/tup-ohos-$$"
mkdir -p "$WORK" || { echo "FAIL: 无法创建可写工作目录 $WORK"; exit 2; }
TMPDIR="$WORK/tmp"; export TMPDIR; mkdir -p "$TMPDIR"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

CC="${CC:-$(command -v clang 2>/dev/null || command -v gcc 2>/dev/null || echo clang)}"

# 选一个真正可 exec 的 shell：本平台 PATH 上排在前的 sh 可能是不可执行的副本
# （execve 被拒 EACCES，rc=126），直接使用会让用例出现与适配无关的假失败，故逐个实跑探测
SHELL_OK=""
for cand in "$(command -v sh 2>/dev/null)" /data/service/hnp/bin/sh /system/bin/sh /bin/sh; do
	if [ -n "$cand" ] && [ -x "$cand" ] && "$cand" -c 'exit 0' 2>/dev/null; then
		SHELL_OK="$cand"
		break
	fi
done
[ -n "$SHELL_OK" ] || SHELL_OK=sh

n=0; nf=0
chk() { # $1=用例名 $2=结果(0 通过/1 失败) $3=证据
	n=$((n + 1))
	if [ "$2" = 0 ]; then
		echo "PASS: $1${3:+ — $3}"
	else
		echo "FAIL: $1${3:+ — $3}"
		nf=$((nf + 1))
	fi
}
evidence() { # 取日志最后一行非空内容
	sed -n '$p' "$1" 2>/dev/null | cut -c1-200
}

echo "--- T1 CLI 与后端（binary=$TUP）---"
v="$("$TUP" --version 2>&1 | sed -n '1p')"
case "$v" in *0.8*) r=0;; *) r=1;; esac
chk "T1a tup --version 报告 0.8（TUP_LABEL 生效）" "$r" "$v"

s="$("$TUP" server 2>&1 | sed -n '1p')"
case "$s" in ldpreload*) r=0;; *) r=1;; esac
chk "T1b tup server = ldpreload（HarmonyOS 平台分支，平台无 /dev/fuse）" "$r" "$s"

echo "--- T2 端到端真实构建（消费者流程）---"
w="$WORK/e2e"; mkdir -p "$w"; cd "$w" || exit 2
cat > main.c <<'EOF'
#include <stdio.h>
int main(void) { puts("hello from tup"); return 0; }
EOF
cat > Tupfile <<EOF
: main.c |> $CC -c %f -o %o |> main.o
: main.o |> $CC %f -o %o |> hello
EOF
"$TUP" init --no-sync --force > init.log 2>&1
"$TUP" > build1.log 2>&1; rc1=$?
if [ "$rc1" = 0 ] && [ -f hello ]; then r=0; else r=1; fi
chk "T2a tup 编译并链接 C 程序（ldpreload 追踪 clang 产出）" "$r" "exit=$rc1 $(evidence build1.log)"

out1="$(./hello 2>&1)"
[ "$out1" = "hello from tup" ] && r=0 || r=1
chk "T2b 运行构建产物得到预期输出" "$r" "输出: ${out1:-无}"

"$TUP" > build2.log 2>&1
if grep -q 'main\.c' build2.log; then r=1; else r=0; fi
chk "T2c 未变更时二次执行不重建（增量判定生效）" "$r" "$(evidence build2.log)"

sleep 1
cat > main.c <<'EOF'
#include <stdio.h>
int main(void) { puts("hello again"); return 0; }
EOF
"$TUP" > build3.log 2>&1; rc3=$?
out3="$(./hello 2>&1)"
if [ "$rc3" = 0 ] && [ "$out3" = "hello again" ]; then r=0; else r=1; fi
chk "T2d 改动源码后增量重建，产物随之更新" "$r" "exit=$rc3 输出: ${out3:-无}"

echo "--- T3 toybox touch 写事件追踪（补丁 0002）---"
w="$WORK/touch-new"; mkdir -p "$w"; cd "$w" || exit 2
printf ': |> touch %%o |> new.txt\n' > Tupfile
"$TUP" init --no-sync --force > init.log 2>&1
"$TUP" > b1.log 2>&1; rc=$?
if [ "$rc" = 0 ] && [ -f new.txt ]; then r=0; else r=1; fi
chk "T3a 规则用 touch 新建输出：首次构建成功（O_CREAT 记为写事件）" "$r" "exit=$rc $(evidence b1.log)"

"$TUP" > b2.log 2>&1
if grep -q 'touch new.txt' b2.log; then r=1; else r=0; fi
chk "T3b 未变更时二次执行不重建" "$r" "$(evidence b2.log)"

w="$WORK/touch-existing"; mkdir -p "$w"; cd "$w" || exit 2
printf 'x\n' > dep.txt
printf ': dep.txt |> %s -c %s |> out2.txt\n' "$SHELL_OK" "'cat %f > /dev/null; touch %o'" > Tupfile
"$TUP" init --no-sync --force > init.log 2>&1
"$TUP" > c1.log 2>&1; rc1=$?
[ -f out2.txt ] && r=$rc1 || r=1
chk "T3c 输出未存在时的首次构建" "$r" "exit=$rc1"

sleep 1; printf 'xxxx\n' > dep.txt
"$TUP" > c2.log 2>&1; rc2=$?
if ! grep -q 'touch out2.txt' c2.log; then rc2=99; fi
if [ "$rc2" = 0 ]; then r=0; else r=1; fi
chk "T3d 输出已存在时重跑同一条 touch 规则（utimensat 路径）仍记为写事件" "$r" "重跑 exit=$rc2 $(evidence c2.log)"

echo "--- T4 只读 /tmp 上的临时文件回退（补丁 0005–0008）---"
w="$WORK/tmpdir-rw"; mkdir -p "$w"; cd "$w" || exit 2
printf ': |> touch %%o |> t.txt\n' > Tupfile
TMPDIR="$WORK/tmp" "$TUP" init --no-sync --force > init.log 2>&1
TMPDIR="$WORK/tmp" "$TUP" > a.log 2>&1; rc=$?
if [ "$rc" = 0 ] && ! grep -qi 'tmpfile.*Permission denied' a.log; then r=0; else r=1; fi
chk "T4a TMPDIR 指向可写目录时构建正常（首选 TMPDIR）" "$r" "exit=$rc $(evidence a.log)"

w="$WORK/tmpdir-ro"; mkdir -p "$w"; cd "$w" || exit 2
printf ': |> touch %%o |> t.txt\n' > Tupfile
TMPDIR=/tmp "$TUP" init --no-sync --force > init.log 2>&1
TMPDIR=/tmp "$TUP" > b.log 2>&1; rc=$?
if [ "$rc" = 0 ] && [ -d .tup/tmp ] && ! grep -qi 'tmpfile.*Permission denied' b.log; then r=0; else r=1; fi
chk "T4b TMPDIR 落在只读 /tmp 时回退项目内 .tup/tmp（平台真实场景）" "$r" \
	"exit=$rc .tup/tmp=$( [ -d .tup/tmp ] && echo 存在 || echo 缺失)"

w="$WORK/tmpdir-empty"; mkdir -p "$w"; cd "$w" || exit 2
printf ': |> touch %%o |> t.txt\n' > Tupfile
TMPDIR= "$TUP" init --no-sync --force > init.log 2>&1
TMPDIR= "$TUP" > c.log 2>&1; rc=$?
if [ "$rc" = 0 ] && [ -d .tup/tmp ] && ! grep -qi 'tmpfile.*Permission denied' c.log; then r=0; else r=1; fi
chk "T4c TMPDIR 为空时同样回退 .tup/tmp（回退链生效）" "$r" "exit=$rc $(evidence c.log)"

echo "--- T5 TMPDIR 传入构建命令（补丁 0004）---"
w="$WORK/env"; mkdir -p "$w"; cd "$w" || exit 2
printf ': |> %s -c %s |> env.txt\n' "$SHELL_OK" "'echo \"TMPDIR=\$TMPDIR\" > %o'" > Tupfile
TMPDIR="$WORK/tmp" "$TUP" init --no-sync --force > init.log 2>&1
TMPDIR="$WORK/tmp" "$TUP" > c.log 2>&1; rc=$?
got="$(cat env.txt 2>/dev/null || true)"
if [ "$rc" = 0 ] && [ "$got" = "TMPDIR=$WORK/tmp" ]; then r=0; else r=1; fi
chk "T5 子进程看到 TMPDIR（默认环境白名单）" "$r" "子进程: ${got:-无}"

echo "--- T6 产物平台一致性 ---"
[ -f "$BINDIR/tup-ldpreload.so" ] && r=0 || r=1
chk "T6a 注入库与可执行文件同目录（depfile.c 硬性要求）" "$r" "$BINDIR"

elf="$(readelf -h "$TUP" 2>/dev/null | grep -E 'Class|Machine' | tr -s ' ' | tr '\n' ' ')"
case "$elf" in *AArch64*) r=0;; *) r=1;; esac
chk "T6b bin/tup 为 aarch64 ELF" "$r" "${elf:-readelf 不可用}"

leaks="$(grep -a -o -E '/storage/|/home/|/Users/' "$TUP" 2>/dev/null | sort -u | tr '\n' ' ')"
if [ -z "$leaks" ]; then r=0; else r=1; fi
chk "T6c 产物无宿主构建路径泄漏" "$r" "${leaks:-无}"

echo
echo "TEST_OHOS_TOTAL=$n"
printf '===== tup 0.8 HarmonyOS 专项用例: %d 项，通过 %d，失败 %d =====\n' "$n" "$((n - nf))" "$nf"
[ "$nf" = 0 ] || exit 1
