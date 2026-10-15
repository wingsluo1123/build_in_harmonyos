#! /bin/sh
# detect-netdb-reentrant-gap.sh — 检测「源码使用 netdb 可重入查询(_r 族)，但目标 libc 未提供」
#
# 用法: sh detect-netdb-reentrant-gap.sh [源码目录] [日志文件] [sysroot]
# 退出码: 0 = 未见风险   1 = 命中风险   2 = 用法/目录错误
#
# 命中判定（两条同时满足）:
#   A. 源码侧: 调用 netdb 的 _r 族可重入查询（getproto*_r / getserv*_r / getnet*_r）
#   B. 目标侧: 目标 sysroot 的 netdb.h 未声明该族（musl/OHOS sysroot 只提供非重入版）
# 后果: 链接期 `undefined symbol: getprotobynumber_r`（lld/ld 直接失败）；
#       若被弱符号或自定义 stub 兜住，运行期恒返回 NULL → 名字退化为数字标签。
#
# 附带提示（运行期，脚本无法在构建期判定，只做静态提示）:
#   协议名/服务名查询依赖 /etc/protocols、/etc/services。这两个文件缺失时
#   getprotobynumber()/getservbyport() 只能返回 NULL，调用方若以 "p%d"/"%d" 回退，
#   上游按名字比对的测试（*.xml_gold / *.json_gold 的 val="udp"/"domain"）会失败。
#
# 输出同时写入 stdout 与日志文件（若给出）；脚本不吞输出、不使用管道 head，避免 SIGPIPE。

set -u

SRC=${1:-.}
LOG=${2:-}
SYSROOT=${3:-}

say() {
  printf '%s\n' "$*"
  if [ -n "$LOG" ]; then printf '%s\n' "$*" >>"$LOG"; fi
  return 0
}

[ -d "$SRC" ] || { say "ERROR: 不是目录: $SRC"; exit 2; }

TMP="${TMPDIR:-/tmp}/netdbgap.$$"
mkdir -p "$TMP" || { say "ERROR: 无法创建临时目录 $TMP"; exit 2; }
trap 'rm -rf "$TMP"' EXIT INT TERM

say "== detect-netdb-reentrant-gap: $SRC"
say "   时间: $(date 2>/dev/null || echo unknown)   临时目录: $TMP"

# ---------------------------------------------------------------- 1. 源码侧扫描
say ""
say "== 1) 源码侧: netdb _r 族调用点"
# 只扫源码/头/构建脚本，避开二进制与版本库元数据
PAT='get(proto|serv|net|addrinfo|nameinfo)[a-z_]*_r[[:space:]]*\('
find "$SRC" -type f \
  \( -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.cxx' \
     -o -name '*.h' -o -name '*.hh' -o -name '*.hpp' \
     -o -name '*.m4' -o -name '*.ac' -o -name '*.am' \
     -o -name 'configure' -o -name 'configure.ac' -o -name 'Makefile.am' \) \
  -exec grep -nE "$PAT" {} + 2>/dev/null >"$TMP/hits.txt" || true
# busybox find 不支持 -exec ... + 时回退逐个文件
if [ ! -s "$TMP/hits.txt" ]; then
  find "$SRC" -type f \
    \( -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
    -exec grep -nE "$PAT" {} \; 2>/dev/null >"$TMP/hits.txt" || true
fi
HITS=$(grep -c . "$TMP/hits.txt" 2>/dev/null || echo 0)
say "   命中调用点: $HITS 处"
if [ "${HITS:-0}" -gt 0 ]; then
  # 只展示前 20 行，用 sed 截断（不用 head，避免 SIGPIPE）
  sed -n '1,20p' "$TMP/hits.txt" | while IFS= read -r line; do say "   $line"; done
  [ "$HITS" -gt 20 ] && say "   ...（其余 $((HITS - 20)) 处见日志/自行 grep）"
fi

# ---------------------------------------------------------------- 2. 目标 sysroot 探测
say ""
say "== 2) 目标侧: sysroot 是否声明 _r 族"
NETDB_H=""
CANDDIRS=""
if [ -n "$SYSROOT" ]; then
  CANDDIRS="$SYSROOT/sysroot/usr/include $SYSROOT/usr/include $SYSROOT/include $SYSROOT"
else
  # 2a. 环境变量（不写死任何本地绝对路径）
  for env_dir in "${OHOS_SYSROOT:-}" "${OHOS_SDK_SYSROOT:-}"; do
    [ -n "$env_dir" ] && [ -d "$env_dir" ] || continue
    CANDDIRS="$CANDDIRS $env_dir/sysroot/usr/include $env_dir/usr/include $env_dir/include $env_dir"
  done
  # 2b. 编译器自报：sysroot + 完整 include 搜索列表（取全部目录，不只第一个——
  #     第一个通常是 clang 内建头目录，里面没有 netdb.h）
  for cc in "${CC:-}" clang cc gcc; do
    [ -n "$cc" ] || continue
    command -v "$cc" >/dev/null 2>&1 || continue
    sysr=$("$cc" -print-sysroot 2>/dev/null || true)
    [ -n "$sysr" ] && CANDDIRS="$CANDDIRS $sysr/sysroot/usr/include $sysr/usr/include"
    "$cc" -E -Wp,-v -xc /dev/null 2>&1 \
      | sed -n '/#include <\.\.\.> search starts here:/,/End of search list/p' \
      | sed -n 's/^[[:space:]]*//;s/[[:space:]]*$//p' \
      >"$TMP/incdirs.txt" 2>/dev/null || true
    while IFS= read -r d; do
      case "$d" in
        ''|*'search starts here:'*|*'End of search list'*) continue ;;
      esac
      [ -d "$d" ] && CANDDIRS="$CANDDIRS $d"
    done <"$TMP/incdirs.txt"
    break   # 找到第一个可用编译器即可
  done
  # 2c. 兜底：标准系统路径（仅当以上全部失败时才会命中）
  CANDDIRS="$CANDDIRS /usr/include"
fi
for d in $CANDDIRS; do
  if [ -f "$d/netdb.h" ]; then NETDB_H="$d/netdb.h"; break; fi
done

MISSING=0
NO_HDR=0
if [ -z "$NETDB_H" ]; then
  say "   未定位到 netdb.h（可用第 3 个参数显式给 sysroot，或导出 OHOS_SYSROOT）"
  say "   → 无法判定目标侧能力；按'目标可能不支持'处理"
  NO_HDR=1
else
  say "   netdb.h: $NETDB_H"
  # 逐个核对源码实际用到的函数名（宽泛匹配整族会漏判：某族里可能只有个别函数缺失）
  grep -oE 'get[a-z_]*_r' "$TMP/hits.txt" 2>/dev/null | sort -u >"$TMP/used.txt" || true
  while IFS= read -r fn; do
    [ -n "$fn" ] || continue
    if grep -qE "${fn}[[:space:]]*\(" "$NETDB_H" 2>/dev/null; then
      say "   [已声明] $fn"
    else
      say "   [未声明] $fn  ← 链接期会 undefined symbol"
      MISSING=$((MISSING + 1))
    fi
  done <"$TMP/used.txt"
  say "   未声明的被用函数: $MISSING 个"
fi

# ---------------------------------------------------------------- 3. 结论
say ""
say "== 3) 判定"
if [ "${HITS:-0}" -eq 0 ]; then
  say "   结果: 未见风险（源码未使用 netdb _r 族；非重入版 API 不受本缺口影响）"
  say "   NETDB_REENTRANT_GAP=absent"
  exit 0
fi
if [ "${NO_HDR:-0}" -eq 1 ] || [ "${MISSING:-0}" -gt 0 ]; then
  say "   结果: 【命中】源码使用了 _r 族，但目标 libc 未声明该族"
  say "   → 链接期会报 undefined symbol（实测 OHOS/musl: getprotobynumber_r / getservbyname_r）"
  say "   → 处置见同目录 strategy.md（补丁模板：libc 能力检测 + 非重入回退 + 内置 IANA 表）"
  say "   附注: 协议名/服务名查询还依赖 /etc/protocols、/etc/services；两者缺失时"
  say "         即便回退到非重入版也只能返回 NULL，按名字比对的测试会退化为数字标签。"
  say "   NETDB_REENTRANT_GAP=hit"
  exit 1
fi
say "   结果: 源码使用 _r 族，目标 libc 已声明该族 → 链接期无缺口"
say "   附注: 运行期仍依赖 /etc/protocols、/etc/services（名字解析），请确认目标根文件系统具备"
say "   NETDB_REENTRANT_GAP=absent"
exit 0
