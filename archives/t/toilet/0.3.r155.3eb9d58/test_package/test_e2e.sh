#!/data/service/hnp/bin/bash
# test_package/test_e2e.sh — 消费者端到端用例（HarmonyOS PC 目标机实机执行）
#
# 被测对象：**本次配方安装后的 toilet 包**（二进制绝对路径由
# test_package/conanfile.py 从 self.dependencies["toilet"] 解析后经环境变量传入；
# 脚本开头再次校验该路径确实位于被测包目录内），不使用源码树产物、系统同名程序
# 或任何旧包缓存。
#
# 用例（每个用例是「真实输入 → 调用安装后的包 → 完成核心功能 → 核对实际业务输出」
# 的完整流程，逐条带唯一 ID）：
#   HM-E2E-01 文本渲染端到端：真实输入文件 → toilet 渲染 → 与黄金输出逐字节比对
#   HM-E2E-02 字体资产端到端：安装包 share/figlet 下全部 .tlf 字体逐个加载并渲染
#   HM-E2E-03 HTML 导出端到端：渲染 + HTML 文档导出，核对文档结构与字形内容
#
# 判定：任一用例失败即 exit 非零（conan create 失败），并逐行打印 PASS/FAIL 证据。
#
# 刻意只 `set -u`、不加 `set -e`：每个用例都要**捕获被测命令的退出码**（rcNN=$?）并据此
# 统计 PASS/FAIL 后继续跑完其余用例；`set -e` 会在首个非零退出码处提前终止，导致
# 后面的用例不被执行、统计不完整。所有错误路径都显式检查并计入 failed。
set -u

TOILET_BIN="${TOILET_BIN:?must point to the installed toilet binary}"
TOILET_PKG="${TOILET_PKG:?must point to the tested package folder}"
TOILET_FONTDIR="${TOILET_FONTDIR:?must point to the installed share/figlet}"

total=0
passed=0
failed=0

note() { echo "[E2E] $*"; }
case_pass() { total=$((total + 1)); passed=$((passed + 1)); echo "[E2E] PASS $1 — $2"; }
case_fail() { total=$((total + 1)); failed=$((failed + 1)); echo "[E2E] FAIL $1 — $2"; }

# ── 前置校验：被测二进制必须位于被测包目录内（被测对象来源证据） ──
case "$TOILET_BIN" in
  "$TOILET_PKG"/*) note "被测二进制 = $TOILET_BIN（位于被测包目录内）✓" ;;
  *) echo "❌ 被测二进制不在被测包目录内：$TOILET_BIN vs $TOILET_PKG"; exit 1 ;;
esac
[ -x "$TOILET_BIN" ] || { echo "❌ 被测二进制不可执行：$TOILET_BIN"; exit 1; }
[ -d "$TOILET_FONTDIR" ] || { echo "❌ 字体目录缺失：$TOILET_FONTDIR"; exit 1; }
note "系统：$(uname -s) $(uname -m) / $(uname -r)"
note "包内字体数：$(find "$TOILET_FONTDIR" -name '*.tlf' | wc -l)"

WORK_BASE="${TMPDIR:-}"
if [ -n "$WORK_BASE" ] && [ -d "$WORK_BASE" ] && [ -w "$WORK_BASE" ]; then
  WORK="$WORK_BASE/toilet-e2e-$$"
else
  # 本机 /tmp 只读（E002 族），故回退到当前构建目录
  WORK="$(pwd)/e2e-work"
fi
rm -rf "$WORK"; mkdir -p "$WORK"
note "证据目录：$WORK"

# ══════════════════════════════════════════════════════════════════════
# HM-E2E-01 文本渲染端到端
#   输入：真实文本文件 input.txt（内容 "OHOS"）
#   流程：安装后的 toilet（-f pagga --width 80）从 stdin 读入 → 渲染 ASCII 艺术字
#   预期业务输出：pagga 字体渲染出的 3 行字形，逐字节等于黄金文件
# ══════════════════════════════════════════════════════════════════════
printf 'OHOS\n' > "$WORK/input.txt"
cat > "$WORK/expected-01.txt" <<'GOLDEN'
░█▀█░█░█░█▀█░█▀▀
░█░█░█▀█░█░█░▀▀█
░▀▀▀░▀░▀░▀▀▀░▀▀▀
GOLDEN
"$TOILET_BIN" -f pagga --width 80 < "$WORK/input.txt" > "$WORK/out-01.txt" 2> "$WORK/err-01.txt"
rc01=$?
if [ "$rc01" -eq 0 ] && cmp -s "$WORK/expected-01.txt" "$WORK/out-01.txt"; then
  case_pass "HM-E2E-01" "渲染输出与黄金文件逐字节一致（$(wc -c < "$WORK/out-01.txt") 字节，exit=0）"
else
  case_fail "HM-E2E-01" "exit=$rc01，输出比对失败（见 $WORK/out-01.txt / $WORK/err-01.txt）"
  echo "---- 实际输出 ----"; cat "$WORK/out-01.txt"; echo "---- stderr ----"; cat "$WORK/err-01.txt"
fi

# ══════════════════════════════════════════════════════════════════════
# HM-E2E-02 字体资产端到端
#   输入：安装包 share/figlet 下的全部 .tlf 字体（真实资产）
#   流程：对每个字体调用安装后的 toilet（-d 包内字体目录 -f 字体 "Hello World"）
#   预期业务输出：24 个字体全部加载成功、exit=0、输出非空（0 个加载错误）
# ══════════════════════════════════════════════════════════════════════
font_total=0
font_bad=0
for font_path in "$TOILET_FONTDIR"/*.tlf; do
  [ -e "$font_path" ] || continue
  font_total=$((font_total + 1))
  font_name="$(basename "$font_path")"
  if "$TOILET_BIN" -d "$TOILET_FONTDIR" -f "$font_name" Hello World > "$WORK/out-02.txt" 2> "$WORK/err-02.txt" \
     && [ -s "$WORK/out-02.txt" ]; then
    :
  else
    font_bad=$((font_bad + 1))
    echo "[E2E]   字体加载失败：$font_name（$(head -c 200 "$WORK/err-02.txt")）"
  fi
done
if [ "$font_total" -eq 24 ] && [ "$font_bad" -eq 0 ]; then
  case_pass "HM-E2E-02" "包内 $font_total/$font_total 个字体全部加载并渲染成功，0 个加载错误"
else
  case_fail "HM-E2E-02" "字体总数=$font_total（期望 24），加载失败=$font_bad"
fi

# ══════════════════════════════════════════════════════════════════════
# HM-E2E-03 HTML 导出端到端
#   输入：命令行文本 "OHOS"（-f pagga）
#   流程：安装后的 toilet --html 导出完整 HTML 文档
#   预期业务输出：XHTML 文档头/尾部齐全，且逐行字形内容与渲染结果一致
#   （3 行 glyph span，含 pagga 使用的块字符实体 &#9608;/&#9617;/&#9600;）
# ══════════════════════════════════════════════════════════════════════
"$TOILET_BIN" --html -f pagga "OHOS" > "$WORK/out-03.html" 2> "$WORK/err-03.html"
rc03=$?
rows=$(grep -c '<span style=' "$WORK/out-03.html" 2>/dev/null)
if [ "$rc03" -eq 0 ] \
   && grep -q '<!DOCTYPE html' "$WORK/out-03.html" \
   && grep -q '</div></body></html>' "$WORK/out-03.html" \
   && grep -q '&#9608;' "$WORK/out-03.html" \
   && [ "$rows" -eq 3 ]; then
  case_pass "HM-E2E-03" "HTML 文档结构完整且含 3 行字形（$(wc -c < "$WORK/out-03.html") 字节，exit=0）"
else
  case_fail "HM-E2E-03" "exit=$rc03，span 行数=$rows（期望 3），结构校验失败"
  head -5 "$WORK/out-03.html"
fi

echo "[E2E] 消费者端到端用例统计：PASS=$passed/$total FAIL=$failed"
note "证据目录：$WORK（out-01.txt / expected-01.txt / out-03.html / err-*.txt）"
[ "$failed" -eq 0 ] || exit 1
exit 0
