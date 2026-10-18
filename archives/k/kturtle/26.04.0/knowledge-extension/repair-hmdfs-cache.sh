#!/bin/sh
# repair-hmdfs-cache.sh — HMDFS 缓存病灶修复策略（知识库拓展四件套 ②）
# 与 detect-hmdfs-exec-integrity.sh 配套，落实 README 记载的实测处置规律：
#
#   拒载（签名失效，R1）/ 幻影（R4）→ 内容级修补不可逆（patchelf/python/tar
#      改写使 .codesign 失效，加载时 Permission denied）。唯一出路是恢复
#      原始字节：conan remove -c + download 重下。本子命令只打印命令清单，
#      不替操作者执行删除（删除是破坏性动作）。
#   C 断链绝对 NEEDED（R5）→ 从可信源逐字节填充目标路径：候选源先做读验证
#      （幻影源会打出空洞），rm 后再 cp（R3：HMDFS 拒绝原地覆盖）。
#   D 相对 NEEDED（R6）→ 代码级策略，不在本脚本（test_package cwdroot 模式，
#      参考本版本目录 test_package/conanfile.py）。
#
# 用法:
#   sh repair-hmdfs-cache.sh plan  <audit-report>            # 拒载/幻影重建清单
#   sh repair-hmdfs-cache.sh fill  <old-cache-p> <report> [fresh-p]
#                                                             # C 填充
# 退出码: 0=完成 / 1=有未修复项 / 2=用法错误
set -u

if [ $# -lt 2 ]; then
  echo "usage: $0 plan <report> | $0 fill <old-cache-p> <report> [fresh-p]" >&2
  exit 2
fi

case "$1" in
plan)
  report="$2"
  [ -f "$report" ] || { echo "ERROR: no report: $report" >&2; exit 2; }
  echo "# 修复计划（在 CONAN_HOME=<被审计缓存> 下执行；<remote> 换成实际 remote 名）:"
  echo "#   受影响顶层包目录（A/B 计数）:"
  awk '$1=="A"||$1=="B" {print $2}' "$report" \
    | sed -n 's|.*/p/\([a-z0-9]\{4,\}\)/.*|\1|p' | sort | uniq -c
  echo
  echo "# 对每个受影响包（把 <pkg>/<ver> 换成对应 reference）:"
  echo '#   conan remove "<pkg>/<ver>" -c && conan download "<pkg>/<ver>" -r=<remote>'
  echo "# 注意: 缓存包目录名是 pkgid 哈希，需按 conan list 或 remove 输出对应 reference。"
  exit 0
  ;;
fill)
  oldp="$2"; report="$3"; freshp="${4:-$oldp}"
  [ -d "$oldp" ] || { echo "ERROR: no such dir: $oldp" >&2; exit 2; }
  [ -f "$report" ] || { echo "ERROR: no report: $report" >&2; exit 2; }
  filled=0; unfilled=0
  # 只取 C 行；格式 "C <referencing-file> -> <target>"，arrow 单独吃掉
  while read -r typ src arrow target; do
    [ "$typ" = "C" ] || continue                       # 非 C 行（A/D/summary）跳过
    case "$target" in /*) ;; *) continue ;; esac       # 只处理绝对路径目标
    [ "${target:-}" ] || continue
    [ -f "$target" ] && continue                       # 已存在，跳过
    base=$(basename "$target")
    tail=${target#*/p/}; dir=${tail%%/p/*}
    mkdir -p "$(dirname "$target")" 2>/dev/null
    ok=""
    for cand in "$freshp/$dir/p/lib/$base" \
                "$(find "$freshp/$dir/p" -name "$base" 2>/dev/null | head -1)" \
                "$(find "$freshp" -path "*/p/lib/$base" 2>/dev/null | head -1)"; do
      [ -n "$cand" ] || continue
      cat "$cand" > /dev/null 2>&1 || continue         # 幻影源，回退下一候选
      rm -f "$target" 2>/dev/null                      # HMDFS 禁原地覆盖
      if cp "$cand" "$target"; then ok=1; echo "FILLED $base -> $dir"; break; fi
    done
    if [ -n "$ok" ]; then filled=$((filled+1)); else unfilled=$((unfilled+1)); echo "UNFILLED $target"; fi
  done < "$report"
  echo "# fill 完成: filled=$filled unfilled=$unfilled；重跑检测脚本确认 C=0"
  [ "$unfilled" -eq 0 ] && exit 0
  exit 1
  ;;
*)
  echo "usage: $0 plan <report> | $0 fill <old-cache-p> <report> [fresh-p]" >&2
  exit 2
  ;;
esac
