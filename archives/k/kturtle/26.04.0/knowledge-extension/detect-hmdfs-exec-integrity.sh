#!/bin/sh
# detect-hmdfs-exec-integrity.sh — OHOS conan cache integrity audit
# (知识库拓展四件套 ① 检测脚本；POSIX sh)
#
# 检测 OHOS HMDFS 开发机上 conan 缓存的文件级病灶（kturtle 26.04.0
# 适配期间实测沉淀，规律详见同目录 README.md §二）：
#
#   A) 咨询项: ELF 无 owner-x 位（660/644，与「曾被无签名意识的工具链
#      改写」强相关——判据仍是加载时 Permission denied，见 README R1/R2）
#   B) 幻影条目      : -f/find 可见但 read() 失败（目录项与数据不一致）
#   C) 断链绝对 NEEDED : DT_NEEDED 记录绝对路径且目标不存在（发布件烙死
#                      构建 worker 的缓存布局，R5；绝对路径优先于
#                      LD_LIBRARY_PATH，必须真实存在）
#   D) 相对 NEEDED   : DT_NEEDED 为 "../.." 形态（按 CWD 解析，不吃
#                      LD_LIBRARY_PATH，R6）
#
#   另：已签名库的内容改写（patchelf/python/tar）使 .codesign 失效 →
#   加载期 Permission denied，无法离线密码学验证，靠 A/C 定位 +
#   README §三 策略恢复原始字节。
#
# 用法: sh detect-hmdfs-exec-integrity.sh [缓存p目录] [输出报告]
#   缺省目录: $HOME/.cache/conan2/p （隔离 CONAN_HOME 场景显式传参，
#   如 "$CONAN_HOME/p"）。
#   报告同时打印到 stdout 并落盘到第二参数（缺省 <缓存目录>/../.cache-audit.txt
#   不可写时用 ${TMPDIR:-/tmp}）。
# 退出码: 0=干净; 1=有发现(C 为致命); 2=用法/环境错误
set -u

CACHE_P="${1:-$HOME/.cache/conan2/p}"
READELF="$(command -v readelf 2>/dev/null || echo /data/service/hnp/bin/readelf)"

[ -d "$CACHE_P" ] || { echo "ERROR: cache dir not found: $CACHE_P" >&2; exit 2; }
[ -x "$READELF" ] || { echo "ERROR: readelf not available ($READELF)" >&2; exit 2; }

REPORT="${2:-}"
[ -n "$REPORT" ] || REPORT="$(dirname "$CACHE_P")/.cache-audit.txt"
if ! : > "$REPORT" 2>/dev/null; then
  REPORT="${TMPDIR:-/tmp}/ohc-cache-audit.txt"
  : > "$REPORT" || { echo "ERROR: cannot write report" >&2; exit 2; }
fi

elog() { echo "$@" | tee -a "$REPORT"; }

A_OUT=0; B_OUT=0; C_OUT=0; D_OUT=0

elog "# ohc-cache-audit report"
elog "# cache: $CACHE_P"
elog "# date : $(date '+%F %T' 2>/dev/null || echo unknown)"
elog ""

# 单趟扫描 .so 与 bin/ 下可执行文件（幻影检测限定同类文件；全树 cat 扫描
# 在大缓存上代价过高——README「限制」一节有说明）
TMP_LIST="${TMPDIR:-/tmp}/.audit-elflist.$$"
find "$CACHE_P" \( -name '*.so' -o -name '*.so.*' -o -path '*/bin/*' \) -type f 2>/dev/null > "$TMP_LIST"
TOTAL=$(wc -l < "$TMP_LIST")

elog "## A) exec-poisoned files (mode without owner-x)"
elog "## B) phantom entries (stat ok, read fails)"
elog "## C) dangling absolute DT_NEEDED"
elog "## D) relative DT_NEEDED (basename view)"
while IFS= read -r f; do
  # B) 幻影：先读验证（同时是 A/C/D 的前置过滤）
  if ! cat "$f" > /dev/null 2>&1; then
    echo "B $f" >> "$REPORT"; B_OUT=$((B_OUT+1)); continue
  fi
  # A) 创建时未带 x 位（HMDFS 事后 chmod 无效）
  mode=$(ls -l "$f" 2>/dev/null | cut -c2-4)
  case "$mode" in
    *x*) ;;
    *) echo "A $f" >> "$REPORT"; A_OUT=$((A_OUT+1)) ;;
  esac
  case "$f" in
    *.so|*.so.*)
      for n in $("$READELF" -d "$f" 2>/dev/null | sed -n 's|.*Shared library: \[\([^]]*\)\].*|\1|p'); do
        case "$n" in
          /*) [ -f "$n" ] || { echo "C $f -> $n" >> "$REPORT"; C_OUT=$((C_OUT+1)); } ;;
          ../*) echo "D $f -> $(basename "$n")" >> "$REPORT"; D_OUT=$((D_OUT+1)) ;;
        esac
      done
      ;;
  esac
done < "$TMP_LIST"
rm -f "$TMP_LIST"

elog ""
elog "## summary  (scanned $TOTAL ELF/bin files)"
elog "A=$A_OUT B=$B_OUT C=$C_OUT D=$D_OUT"
elog "# A/B: 用 repair-hmdfs-cache.sh plan 生成 remove-c+重下清单（conan 自建=唯一可信）"
elog "# C:   用 repair-hmdfs-cache.sh fill 填充（源读验证 + rm+cp，禁原地覆盖）"
elog "# D:   test_package 采用 cwdroot 模式（见 README §D）"

cat "$REPORT"
[ "$C_OUT" -gt 0 ] && exit 1
[ $((A_OUT+B_OUT+D_OUT)) -gt 0 ] && exit 1
exit 0
