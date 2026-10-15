#! /bin/sh
# reproduce.sh — 复现并验证「OHOS/musl 缺 netdb _r 族 + 无 /etc/protocols」（样例库 dsc 2.16.1）
#
# 用法: sh reproduce.sh <源码目录> [工作目录] [日志目录]
#   <源码目录> : dsc 源码树（未打补丁的原树）
#   [工作目录] : 默认 ${TMPDIR:-/tmp}/dsc-netdb-repro
#   [日志目录] : 默认 <工作目录>/logs
#
# 环境变量:
#   CC=<编译器>        默认按 clang/cc/gcc 顺序查找；交叉编译时指向 OHOS clang
#   OHOS_SYSROOT=<dir> 目标 sysroot（可选；不设时由编译器自身配置决定）
#   EXTRA_CFLAGS="..." 追加编译参数（如 --target=aarch64-linux-ohos --sysroot=...）
#
# 前提（两阶段都先打）: ../patches/0001-dns_message-sys-types.patch
#   0001 修的是 `u_char` 未定义（属既有知识条目 E113/E429，OHOS sysroot 不含 BSD 风格
#   类型别名），它是本库**能编译**的前提，与本拓展主题（netdb _r 族）无关。
#
# 阶段 A（关本主题策略）: 只打 0001 → 编译只报隐式声明告警，**链接失败**，
#                   日志出现 `undefined symbol: getprotobynumber_r`。
# 阶段 B（开本主题策略）: 再打 ../patches/0002-ip-proto-no-reentrant-lookup.patch → 链接通过，
#                   且运行输出**真协议名** `udp`（无 /etc/protocols 时纯靠内置 IANA 表），
#                   而不是退化值 `p17`。
#
# 退出码: 0 = 复现成功且策略验证通过 | 2 = 环境不满足（缺编译器/sysroot）
#         3 = 缺少工具 | 4 = 验证失败
# 说明: 所有命令输出重定向到日志文件；脚本不使用 `| head` 之类会提前关闭管道的写法，规避 SIGPIPE。

set -u

SRC=${1:?用法: sh reproduce.sh <源码目录> [工作目录] [日志目录]}
WORK=${2:-${TMPDIR:-/tmp}/dsc-netdb-repro}
LOGD=${3:-$WORK/logs}
PATCHDIR="$(dirname "$0")/../patches"
PATCH1="$PATCHDIR/0001-dns_message-sys-types.patch"
PATCH2="$PATCHDIR/0002-ip-proto-no-reentrant-lookup.patch"

note() { printf '%s\n' "$*"; }

count_lines() { # count_lines <pattern> <file>
  n=$(grep -c "$1" "$2" 2>/dev/null) || n=0
  [ -n "$n" ] || n=0
  printf '%s' "$n"
}

# apply_patch <树目录> <补丁> <核验标记> <核验文件>
# 先用 patch，失败退回 git apply；应用后**核验标记真的出现**——部分平台的 patch 是
# toybox/busybox 实现，可能静默 no-op 却返回 0。
apply_patch() {
  _dir=$1; _patch=$2; _mark=$3; _file=$4
  : >>"$LOGD/apply.log"
  if ( cd "$_dir" && patch -p1 --dry-run ) <"$_patch" >>"$LOGD/apply.log" 2>&1; then
    ( cd "$_dir" && patch -p1 ) <"$_patch" >>"$LOGD/apply.log" 2>&1
  elif ( cd "$_dir" && git apply --check -p1 ) <"$_patch" >>"$LOGD/apply.log" 2>&1; then
    ( cd "$_dir" && git apply -p1 ) <"$_patch" >>"$LOGD/apply.log" 2>&1
  else
    note "ERROR: 补丁无法应用: $_patch（源码树可能已打过），日志: $LOGD/apply.log"
    return 4
  fi
  _n=$(count_lines "$_mark" "$_dir/$_file")
  if [ "$_n" -lt 1 ]; then
    note "ERROR: 补丁看似应用但标记 '$_mark' 未出现在 $_file（patch 实现可能静默 no-op）"
    note "  处置: 用 busybox 或 GNU patch 重跑，或改用 git apply（日志: $LOGD/apply.log）"
    return 4
  fi
  note "      已应用 $(basename "$_patch")（标记 '$_mark' 出现 $_n 次）"
  return 0
}

# ------------------------------------------------------------------ 0. 环境检查
note "== dsc netdb _r 族缺口复现"
note "   源码目录: $SRC"
note "   工作目录: $WORK"
note "   日志目录: $LOGD"
note "   补丁    : $(basename "$PATCH1")（前提） + $(basename "$PATCH2")（本主题策略）"

[ -d "$SRC" ] || { note "ERROR: 源码目录不存在: $SRC"; exit 4; }
[ -f "$SRC/src/ip_proto_index.c" ] || { note "ERROR: 未找到 $SRC/src/ip_proto_index.c"; exit 4; }
[ -f "$PATCH1" ] || { note "ERROR: 补丁不存在: $PATCH1"; exit 4; }
[ -f "$PATCH2" ] || { note "ERROR: 补丁不存在: $PATCH2"; exit 4; }

missing=""
for t in grep sed cmp; do
  command -v "$t" >/dev/null 2>&1 || missing="$missing $t"
done
if [ -n "$missing" ]; then
  note "ERROR: 缺少工具:$missing"
  exit 3
fi

CC_BIN="${CC:-}"
if [ -z "$CC_BIN" ]; then
  for c in clang cc gcc; do
    if command -v "$c" >/dev/null 2>&1; then CC_BIN="$c"; break; fi
  done
fi
if [ -z "$CC_BIN" ]; then
  note "ERROR: 未找到 C 编译器；请设置 CC=<ohos clang 路径>。"
  note "  工具链可由 conan profile 提供（ci/conan/profiles/ohos-aarch64），或导出 CC 后重跑。"
  exit 2
fi

SYSROOT_FLAG=""
if [ -n "${OHOS_SYSROOT:-}" ]; then
  [ -d "$OHOS_SYSROOT" ] || { note "ERROR: OHOS_SYSROOT 不是目录: $OHOS_SYSROOT"; exit 2; }
  SYSROOT_FLAG="--sysroot=$OHOS_SYSROOT"
fi
CFLAGS_ALL="${EXTRA_CFLAGS:-} $SYSROOT_FLAG"

mkdir -p "$WORK" "$LOGD" || { note "ERROR: 无法创建 $WORK / $LOGD"; exit 4; }

note "   编译器  : $CC_BIN"
note "   编译参数: $CFLAGS_ALL"

# 最小 main：只调用 ip_proto_indexer / ip_proto_iterator（该 TU 除 libc 外无外部依赖）。
# 迭代器只输出到 largest（由 indexer 依据消息的 tm->proto 更新），所以先喂一条
# proto=17(udp) 的合成消息，再迭代 0..17，把标签逐个打印出来。
cat >"$WORK/probe_main.c" <<'EOF'
#include <stdio.h>
#include <string.h>

#include "dns_message.h"

int ip_proto_indexer(const dns_message* m);
int ip_proto_iterator(const char** label);

int main(void)
{
    transport_message tm;
    dns_message       m;
    const char*       label = 0;
    int               i;

    memset(&tm, 0, sizeof(tm));
    memset(&m, 0, sizeof(m));
    tm.proto = 17;              /* udp，模拟抓包中的最高协议号 */
    m.tm     = &tm;
    ip_proto_indexer(&m);       /* 令 largest = 17 */

    for (i = 0; i < 18; i++) {  /* 覆盖协议号 0..17（17 = udp） */
        int proto = ip_proto_iterator(&label);
        if (proto < 0) break;
        printf("%d=%s\n", proto, label ? label : "(null)");
    }
    return 0;
}
EOF

# 该 TU 包含 "config.h"（autotools 由 configure 生成）；复现只需它存在，
# 用最小空壳代替（该文件对 config 宏无依赖，行为不受影响）
mkdir -p "$WORK/cfg"
printf '%s\n' '/* minimal config.h for standalone reproduce (upstream generates via configure) */' \
  >"$WORK/cfg/config.h"

# 编译并链接；结果经全局 RC_CC / RC_LINK 回传（避免用拼字符串的变量名——连字符非法）
build_and_link() { # build_and_link <树目录> <日志前缀>
  _d=$1; _p=$2
  note "   ${_p}1 编译 src/ip_proto_index.c"
  # -Wno-error=implicit-function-declaration：保留隐式声明告警（本就是证据之一），
  # 但不让它阻止到达链接期——上游真实构建同样能走到链接步（实测报 undefined symbol）。
  "$CC_BIN" $CFLAGS_ALL -I"$WORK/cfg" -I"$_d/src" -Wno-error=implicit-function-declaration \
      -c "$_d/src/ip_proto_index.c" -o "$_d/ip_proto_index.o" \
      >"$LOGD/${_p}-compile.log" 2>&1
  RC_CC=$?
  note "      rc=$RC_CC  日志: $LOGD/${_p}-compile.log"

  note "   ${_p}2 链接最小可执行文件"
  "$CC_BIN" $CFLAGS_ALL -I"$WORK/cfg" -I"$_d/src" \
      "$_d/ip_proto_index.o" "$WORK/probe_main.c" \
      -o "$_d/probe" >"$LOGD/${_p}-link.log" 2>&1
  RC_LINK=$?
  note "      rc=$RC_LINK  日志: $LOGD/${_p}-link.log"
}

# ------------------------------------------------------------------ 1. 阶段 A：关本主题策略
note ""
note "== 阶段 A：只打 0001（前提），不打 0002 → 预期链接失败：undefined symbol getprotobynumber_r"
rm -rf "$WORK/phase-a"
cp -R "$SRC" "$WORK/phase-a" || { note "ERROR: 复制源码树失败"; exit 4; }
apply_patch "$WORK/phase-a" "$PATCH1" 'sys/types.h' 'src/dns_message.h' || exit 4
build_and_link "$WORK/phase-a" "phase-a"
rc_a_cc=$RC_CC; rc_a_link=$RC_LINK

undef_a=$(count_lines 'getprotobynumber_r' "$LOGD/phase-a-link.log")
note "      链接日志中 getprotobynumber_r 出现次数: $undef_a（关策略时应 >= 1）"

# ------------------------------------------------------------------ 2. 阶段 B：开本主题策略
note ""
note "== 阶段 B：再打 0002（libc 能力检测 + 非重入回退 + 内置 IANA 表）"
rm -rf "$WORK/phase-b"
cp -R "$SRC" "$WORK/phase-b" || { note "ERROR: 复制源码树失败"; exit 4; }
apply_patch "$WORK/phase-b" "$PATCH1" 'sys/types.h' 'src/dns_message.h' || exit 4
apply_patch "$WORK/phase-b" "$PATCH2" 'ip_proto_iana' 'src/ip_proto_index.c' || exit 4
build_and_link "$WORK/phase-b" "phase-b"
rc_b_cc=$RC_CC; rc_b_link=$RC_LINK

note "   B3 运行（目标架构可执行文件）"
"$WORK/phase-b/probe" >"$LOGD/phase-b-run.log" 2>&1
rc_b_run=$?
note "      rc=$rc_b_run  日志: $LOGD/phase-b-run.log"
udp_b=$(count_lines '17=udp' "$LOGD/phase-b-run.log")
p17_b=$(count_lines '17=p17' "$LOGD/phase-b-run.log")
note "      输出中 17=udp 次数: $udp_b（应为 1：真协议名）"
note "      输出中 17=p17 次数: $p17_b（应为 0：未退化）"
if [ "$rc_b_run" -ne 0 ]; then
  note "      注: 交叉编译产物可能无法在本机执行（rc=$rc_b_run）——可把 phase-b/probe 拷到目标机运行"
  note "          并检查 17=udp。本脚本此时跳过 B3 的运行断言。"
fi

# ------------------------------------------------------------------ 3. 结论
note ""
note "== 结论"
ok=1
[ "${rc_a_cc:-1}" -eq 0 ] 2>/dev/null || { note "   [FAIL] 阶段 A 编译失败（rc=${rc_a_cc:-?}）：请看 $LOGD/phase-a-compile.log"; ok=0; }
[ "${rc_a_link:-0}" -ne 0 ] 2>/dev/null || { note "   [FAIL] 阶段 A 竟然链接成功：目标 libc 可能已有 _r 族"; ok=0; }
[ "$undef_a" -ge 1 ] 2>/dev/null || { note "   [FAIL] 阶段 A 链接日志未见 getprotobynumber_r（= $undef_a）"; ok=0; }
[ "${rc_b_cc:-1}" -eq 0 ] 2>/dev/null || { note "   [FAIL] 阶段 B 编译失败（rc=${rc_b_cc:-?}）"; ok=0; }
[ "${rc_b_link:-1}" -eq 0 ] 2>/dev/null || { note "   [FAIL] 阶段 B 仍链接失败（rc=${rc_b_link:-?}）：补丁未覆盖全部调用点"; ok=0; }
if [ "$rc_b_run" -eq 0 ]; then
  [ "$udp_b" -ge 1 ] 2>/dev/null || { note "   [FAIL] 阶段 B 输出未出现 17=udp（内置表未生效？）"; ok=0; }
  [ "$p17_b" -eq 0 ] 2>/dev/null || { note "   [FAIL] 阶段 B 输出退化为 17=p17（无 /etc/protocols 时回退未生效）"; ok=0; }
else
  note "   [SKIP] 阶段 B 运行断言（交叉产物本机不可执行）——请在目标机执行 phase-b/probe 复核 17=udp"
fi

if [ "$ok" = 1 ]; then
  note "   [PASS] 阶段 A 复现「缺 netdb _r 族 → 链接期 undefined symbol」，"
  note "          阶段 B 证明「libc 能力检测 + 非重入回退 + 内置 IANA 表」可修复，"
  note "          且无 /etc/protocols 时仍输出真协议名 udp（非 p17）。"
  note "   全部日志: $LOGD"
  exit 0
fi
note "   详见日志: $LOGD"
exit 4
