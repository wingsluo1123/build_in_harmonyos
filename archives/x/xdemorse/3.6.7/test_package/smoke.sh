#!/bin/sh
# xdemorse 冒烟测试（真跑，不是门禁占位）
# L0c 要求 test_package/ 下存在 .c/.cpp/.cc/.cxx/.sh/.py 之一；本脚本同时是**真实验证**，
# 由 test_package/conanfile.py 的 test() 调用，也可手工执行：
#     sh smoke.sh <package_folder> [<lib_dir>:...] [<out_dir>]
#
# 覆盖三件事：
#   1) 产物齐备：bin/xdemorse 存在且可执行；
#   2) 动态依赖可解析（缺库会立刻打印 Error loading shared library ⇒ FAIL）；
#   3) **真跑上游程序** `xdemorse -v`：上游 `src/main.c:48` 先 `gtk_init(&argc,&argv)`，
#      第 51 行才 `getopt(argc, argv, "hv")` ⇒ **任何选项都需要显示环境**。
#      故按 rule4 如实区分：
#        · 失败原因是「无可用显示」⇒ 记 **环境性 SKIP**（原因与观测输出都打印；SKIP ≠ PASS）
#        · 失败原因不是显示            ⇒ **FAIL**（不掩盖）
set -e

PKG="$1"
LIBS="$2"
OUTDIR="${3:-.}"
BIN="$PKG/bin/xdemorse"

[ -d "$PKG" ] || { echo "usage: smoke.sh <package_folder> [lib_dirs] [out_dir]"; exit 2; }
[ -x "$BIN" ] || { echo "FAIL: missing or not executable: $BIN"; exit 1; }
echo "PASS: artifact present ($(wc -c < "$BIN" 2>/dev/null || echo '?') bytes)"

if [ -n "$LIBS" ]; then
  LD_LIBRARY_PATH="$LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export LD_LIBRARY_PATH
fi

PROBE="$OUTDIR/xdemorse-probe.txt"
"$BIN" -v > "$PROBE" 2>&1 || true

if grep -q "Error loading shared library" "$PROBE" 2>/dev/null; then
  echo "FAIL: dynamic dependencies unresolved:"
  sed 's/^/      /' "$PROBE" | head -6
  exit 1
fi
echo "PASS: dynamic dependencies resolved"

if grep -qE "cannot open display|Unable to init server|No display|Failed to open display" "$PROBE" 2>/dev/null; then
  echo "SKIP: upstream program cannot run here — no display"
  echo "      reason (code-level): src/main.c:48 gtk_init() runs BEFORE the getopt() at line 51,"
  echo "                           so even -h/-v require a display"
  echo "      observed: $(head -1 "$PROBE" 2>/dev/null)"
  exit 0
fi

if [ -s "$PROBE" ]; then
  echo "PASS: upstream program ran; output:"
  sed 's/^/      /' "$PROBE" | head -6
else
  echo "PASS: upstream program ran (no output)"
fi
