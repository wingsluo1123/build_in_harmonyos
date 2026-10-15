#!/bin/bash
# R51 复现脚本 — spot 2.15.1 上游测试套件（`make check`，OHOS 真机执行）
#
# 用法（在真机，对已完成 configure 的构建目录，例如 conan create 的 build 目录）：
#   bash reports/run-upstream-tests.sh <spot-build-dir> [jobs]
#
# 环境适配八点（测试逻辑零改动，均为 OHOS 平台限制的环境侧等价物）：
#   1) SHELL/CONFIG_SHELL=/bin/sh —— profile/环境钉死的 /data/service/hnp/bin/bash
#      在部分 HMBS 主机缺失，make 递归与测试脚本会以 Error 127 失败
#   2) TMPDIR 指向构建目录下可写 tmp —— OHOS /tmp 为只读挂载（E002）
#   3) -jN 并行（默认 4）：真机 nproc=20，但构建期需控制并发避免进程配额压力
#   4) LOG_COMPILER="${SHELL} ./run" —— OHOS 拒绝直接 execve #! 脚本
#      （EACCES；同权限下 ELF 可执行）：automake 并行测试框架默认直接 exec
#      测试驱动 ./run，经 LOG_COMPILER 前置解释器即可（automake 官方机制）；
#      上游 ./run 内部对 .test 本就用 `sh -x`、对 .pl 用 `perl` 显式解释
#   5) libtool 包装脚本转换 —— 构建树里 bin/<tool> 等是 libtool 生成的
#      #! 包装脚本（设好 LD_LIBRARY_PATH 再转调 .libs/ 真身），OHOS 同样
#      拒绝直执；而上游用例经 PATH 直接调用工具名。两遍法：第一遍
#      `make check TESTS=` 只构建（含 check_PROGRAMS，不跑用例），随后把
#      全部包装脚本原地替换为其 .libs/ 真身 ELF，并导出 LD_LIBRARY_PATH
#      覆盖构建树全部 .libs 目录（与包装脚本自身所设环境等价）
#   6) 第二遍为证据轮：在完成上述替换/环境后真实执行全部用例
#   7) LD_PRELOAD 垫片（reports/spot-shexec-shim.c）—— 上游 ltlcross* 用例
#      运行期用 heredoc 生成 `fake` 翻译器脚本并 chmod +x，由 ltlcross/ltldo
#      经 posix_spawnp 直执；OHOS 拒脚本 execve（`sh -c` 也 126，无 ENOEXEC
#      回退）。垫片把"spawn #! 脚本"改写为 /bin/sh <script>（正常平台等价
#      语义，上游测试零改动），ELF 目标原样透传
#   8) GNU grep（style.test）：设备默认 grep 为 toybox（UTF-8 感知、不理会
#      LC_ALL=C）→ style.test 对 << "〈" 等多字节字形误报（其源码注释已预告
#      此类实现差异）；脚本把设备自带 GNU grep（/data/service/hnp/bin/grep）
#      封装到私有目录并前置 PATH（仅替换 grep 解析，不遮蔽其余工具）
#
# 说明：脚本对构建目录代码只读，写入测试产物（check-build.log/check.log、
# 以及被替换的包装脚本路径——该替换仅发生在构建树副本内）。
set -uo pipefail
# 不用 -e：需保留 make 退出码——经 rc 变量输出 [run-upstream-tests] 汇总行后
# 以其退出；-e 会在 make 失败时提前中断、丢失 rc 与汇总行。

ROOT=${1:?用法: $0 <spot-build-dir> [jobs]}
JOBS=${2:-4}
if [ ! -f "${ROOT%/}/Makefile" ]; then
    echo "找不到 ${ROOT%/}/Makefile —— 参数应为已 configure 的构建目录"
    exit 2
fi

# 脚本自身目录必须在 cd 进构建树之前解析（$0 可能是相对路径，cd 后已无法解析；
# 首版 v4 实测踩坑：垫片块内相对 $0 解析失败 → 垫片被静默跳过）
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

export SHELL=/bin/sh
export CONFIG_SHELL=/bin/sh
export TMPDIR="${ROOT%/}/tmp"
mkdir -p "$TMPDIR"

# ── GNU grep（style.test 的语义前提）──
# 上游 style.test 的规则按 GNU grep 语义编写（尊重 LC_ALL=C 的字节匹配）；
# 设备默认 grep 为 toybox 0.8.12——UTF-8 感知且不理会 LC_ALL=C，对
# << "〈" / << "̅" 这类多字节字形产生误报（style.test 源码注释已预告"grep
# 实现无视 LC_ALL=C"的情形；本场景实测命中。设备自带 GNU grep 位于
# /data/service/hnp/bin/grep，其目录含整套工具链、不能整目录前置（会连带
# 遮蔽 sed/awk）；此处仅把它封装为私有 grep 后置于 PATH 之前。
if ! (grep --color=auto -n --version) >/dev/null 2>&1; then
    GNU_GREP=${SPOT_GNU_GREP:-/data/service/hnp/bin/grep}
    if [ -x "$GNU_GREP" ] && ("$GNU_GREP" --color=auto -n --version) >/dev/null 2>&1; then
        TOOLBIN="${TMPDIR}/toolbin"
        mkdir -p "$TOOLBIN"
        cat > "${TOOLBIN}/grepwrap.c" <<WRAPEOF
#include <unistd.h>
int main(int c, char** v){ v[0]="grep"; execv("${GNU_GREP}", v); return 127; }
WRAPEOF
        if /data/service/hnp/bin/clang -O2 -o "${TOOLBIN}/grep" "${TOOLBIN}/grepwrap.c" 2>/dev/null; then
            chmod 755 "${TOOLBIN}/grep" 2>/dev/null || true
            export PATH="${TOOLBIN}:$PATH"
            echo "[run-upstream-tests] 设备默认 grep 非 GNU（UTF-8 误报风险）→ 已封装 ${GNU_GREP} 前置 PATH：${TOOLBIN}/grep"
        else
            echo "[run-upstream-tests] ⚠ GNU grep 封装失败；style.test 可能因 toybox 多字节误报失败"
        fi
    else
        echo "[run-upstream-tests] ⚠ 未找到 GNU grep（$GNU_GREP）；style.test 可能因工具实现差异失败"
    fi
fi

cd "${ROOT%/}"

# ── 第一遍：只构建（TESTS= 置空 → check_PROGRAMS 与工具全部落盘，不跑用例）──
make -j"${JOBS}" check TESTS= > check-build.log 2>&1
bld_rc=$?
echo "[run-upstream-tests] make check TESTS= rc=${bld_rc}（仅构建轮，日志 $(pwd)/check-build.log）"
if [ "${bld_rc}" -ne 0 ]; then
    echo "[run-upstream-tests] 构建轮失败，未进入证据轮；见 $(pwd)/check-build.log"
    exit "${bld_rc}"
fi

# ── 包装脚本 → .libs 真身 ELF（OHOS 拒 #! 直执；判据：可执行且以 #! 开头）──
converted=0
for libs in $(find . -type d -name .libs); do
    parent=${libs%/.libs}
    for real in "$libs"/*; do
        [ -f "$real" ] || continue
        name=${real##*/}
        wrapper="$parent/$name"
        if [ -f "$wrapper" ] && [ -x "$wrapper" ] && \
           [ "$(head -c 2 "$wrapper" 2>/dev/null)" = "#!" ]; then
            cp -f "$real" "$wrapper"
            chmod 755 "$wrapper" 2>/dev/null || true
            converted=$((converted + 1))
        fi
    done
done
# 必须绝对路径：各测试目录下 cwd 不同（tests/、buddy/src/……），相对
# LD_LIBRARY_PATH 条目会在 cd 后解析到错误位置 → 转换后的 ELF 找不到
# libspot.so/libbddx.so（musl: Error relocating ... symbol not found；首轮实测）
LIBS=$(find "${ROOT%/}" -type d -name .libs | tr '\n' ':')
export LD_LIBRARY_PATH="$LIBS${LD_LIBRARY_PATH:-}"
nlibs=$(printf '%s' "$LIBS" | tr ':' '\n' | grep -c .)
echo "[run-upstream-tests] 转换 ${converted} 个 libtool 包装脚本为真身 ELF；LD_LIBRARY_PATH 覆盖 ${nlibs} 个 .libs 目录"

# ── 脚本 spawn 垫片（LD_PRELOAD）：上游用例运行期用 heredoc 生成 `fake`
#    翻译器脚本并 chmod +x，由 ltlcross/ltldo 经 posix_spawnp 直接执行；
#    OHOS 拒绝脚本 execve（sh -c 也 126，无 ENOEXEC 回退）→ 垫片把"spawn
#    脚本"改写为 /bin/sh <script>（POSIX 正常平台语义的等价物，上游测试
#    零改动）；ELF 目标原样透传。源码=reports/spot-shexec-shim.c（真机构建）
SHIM_SRC="$SCRIPT_DIR/spot-shexec-shim.c"
SHIM_SO="$SCRIPT_DIR/spot-shexec-shim.so"
if [ -f "$SHIM_SRC" ]; then
    if [ -f "$SHIM_SO" ] || \
       /data/service/hnp/bin/clang -shared -fPIC -O2 -o "$SHIM_SO" "$SHIM_SRC" 2>/dev/null; then
        export LD_PRELOAD="$SHIM_SO${LD_PRELOAD:+:$LD_PRELOAD}"
        echo "[run-upstream-tests] 脚本 spawn 垫片就绪：$SHIM_SO（LD_PRELOAD）"
    else
        echo "[run-upstream-tests] ⚠ 垫片构建失败：$SHIM_SRC（脚本 spawn 用例将按平台限制失败）"
    fi
fi

# ── 第二遍（证据轮）：真实执行上游用例 ──
# 上游两处 TESTS 驱动方式不同，分目录执行（等价于 make check --k 递归的全部范围）：
#   a) buddy/src：TESTS=bddtest（编译型 check_PROGRAM，上游无 LOG_COMPILER），
#      经上一步转换为真身 ELF 后由 automake 默认驱动直接 exec —— ELF 可直执
#   b) tests/：上游自带 LOG_COMPILER=./run（#! 脚本，直执被 OHOS 拒），
#      命令行前置 ${SHELL} 显式解释器（automake 官方机制）覆盖之
# 注：全局覆盖 LOG_COMPILER 不可行——./run 仅存在于 tests/，会给
#     buddy/src 的 bddtest 拼出 `sh ./run bddtest` → 127（首轮实测）。
B="${ROOT%/}"
cd "$B/buddy/src"
make -k check -j"${JOBS}" > check-buddy.log 2>&1
rc_b=$?
echo "[run-upstream-tests] buddy/src check rc=${rc_b}（日志 $B/buddy/src/check-buddy.log）"

cd "$B/tests"
make -k check -j"${JOBS}" LOG_COMPILER="${SHELL} ./run" > check.log 2>&1
rc_t=$?
echo "[run-upstream-tests] tests check -j${JOBS} rc=${rc_t}（证据轮；完整输出见 $B/tests/check.log）"
if [ "${rc_t}" -eq 0 ]; then exit "${rc_b}"; else exit "${rc_t}"; fi
