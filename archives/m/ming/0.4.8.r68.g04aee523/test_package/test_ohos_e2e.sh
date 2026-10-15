#!/bin/sh
# 鸿蒙特有端到端消费者用例 —— 只用被测包【已安装】的产物，跑通完整 SWF 工具链。
#
# 为什么是「鸿蒙特有」：
#   1) 工作目录必须落在 $TMPDIR：本平台 /tmp 只读，硬编码 /tmp 会失败（E002）。
#      上游 util/main.c 原先把 cws2fws() 的临时文件写死为 /tmp/swftoscriptXXXXXX，
#      本仓库以 patches/0001-util-main.c.patch 改为优先取 TMPDIR —— 本用例的
#      listswf/listaction 步骤（读压缩 SWF）正是该补丁的生效路径。
#   2) makeswf 预处理 .as 需经 clang -E —— OHOS 不提供 cpp，这是本次适配的
#      patches/0002-util-makeswf_utils.c.patch；本用例的编译步骤覆盖它。
#   3) 被测二进制由 OHOS clang 构建，运行期依赖靠 ELF RUNPATH 定位 conan 依赖库
#      （本平台 LD_LIBRARY_PATH 无法穿透 make 子进程链，见配方 generate() 注释）。
#
# 流程（三段已安装工具串成端到端链路，逐环节断言）：
#   makeswf   : ActionScript(.as) --编译--> SWF(CWS)   【库写入 + ActionScript 编译器 + 预处理】
#   listswf   : SWF --反解析--> 结构文本                【库的解析面；含压缩解压路径】
#   listaction: SWF --反解析--> 动作文本                【第二条独立解析链路】
#
# 已知上游限制（不在本用例断言、已在 notes.md/PR 记录）：swftophp/swftocxx 等
# swfto* 转译工具（util/outputscript.c）在「只有动作的 SWF」上 SIGSEGV（rc=139，
# 输出部分内容后崩溃）。该崩溃与本次平台适配无关：同一次运行的 listswf 走同一条
# cws2fws 临时文件路径且完全正常，问题在代码生成路径。
#
# 用法: sh test_ohos_e2e.sh <package_folder>
set -u

PKG="${1:?用法: sh test_ohos_e2e.sh <package_folder>}"
SELF_DIR=$(cd "$(dirname "$0")" && pwd)
AS_FILE="$SELF_DIR/test_ohos_e2e.as"
WORK="${TMPDIR:-/tmp}/ming-ohos-e2e-$$"
MARKER="ming-ohos-e2e-ok"

PASS=0
FAIL=0
ok()  { echo "ok   $1"; PASS=$((PASS + 1)); }
bad() { echo "FAIL $1"; FAIL=$((FAIL + 1)); }

# 让已安装的工具与其依赖库可被找到（等价于 conanrun 的运行期环境）
PATH="$PKG/bin:$PATH"
LD_LIBRARY_PATH="$PKG/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH LD_LIBRARY_PATH

# 1) 已安装工具齐备性
for t in makeswf listswf listaction; do
    if [ -x "$PKG/bin/$t" ]; then ok "已安装 bin/$t"; else bad "缺少 bin/$t"; fi
done

mkdir -p "$WORK" || { echo "FAIL 无法创建 $WORK"; exit 1; }
cd "$WORK" || exit 1

# 2) makeswf: ActionScript -> SWF（内部经 clang -E 预处理；默认 zlib 压缩 → CWS）
makeswf -o e2e.swf -s 320x240 -r 12 -v 6 "$AS_FILE" > makeswf.log 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then ok "makeswf 编译 ActionScript → SWF (rc=0)"; else bad "makeswf 失败 rc=$rc"; sed -n '1,20p' makeswf.log; fi

if [ -s e2e.swf ]; then ok "生成 e2e.swf（$(wc -c < e2e.swf) 字节）"; else bad "未生成 e2e.swf"; fi

# 3) 产物魔数：未压缩 FWS / zlib 压缩 CWS
sig=$(dd if=e2e.swf bs=1 count=3 2>/dev/null)
case "$sig" in
    FWS | CWS) ok "SWF 魔数正确: $sig" ;;
    *) bad "SWF 魔数异常: '$sig'" ;;
esac

# 4) listswf: SWF -> 结构文本（压缩 SWF 会走 cws2fws()，即 TMPDIR 补丁路径）
listswf e2e.swf > listswf.out 2>&1
if [ $? -eq 0 ] && [ -s listswf.out ]; then ok "listswf 反解析成功（$(wc -l < listswf.out) 行）"; else bad "listswf 失败或输出为空"; fi
if grep -q "File version" listswf.out; then ok "listswf 输出含 SWF 头信息（File version）"; else bad "listswf 输出缺 SWF 头信息"; fi
if grep -q "SWFACTION_TRACE" listswf.out; then ok "listswf 输出含 SWFACTION_TRACE 动作"; else bad "listswf 输出缺 SWFACTION_TRACE"; fi
if grep -q "$MARKER" listswf.out; then ok "listswf 输出含本用例写入的常量 \"$MARKER\"（端到端闭环）"; else bad "listswf 输出缺常量 \"$MARKER\""; fi

# 5) listaction: SWF -> 动作文本（第二条独立解析链路）
listaction e2e.swf > listaction.out 2>&1
if [ $? -eq 0 ] && [ -s listaction.out ]; then ok "listaction 反解析成功（$(wc -l < listaction.out) 行）"; else bad "listaction 失败或输出为空"; fi
if grep -q "$MARKER" listaction.out; then ok "listaction 输出含常量 \"$MARKER\""; else bad "listaction 输出缺常量 \"$MARKER\""; fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "PASSED: $PASS 项通过, 0 项失败"
    rc=0
else
    echo "FAILED: $PASS 项通过, $FAIL 项失败"
    rc=1
fi
rm -rf "$WORK"
exit $rc
