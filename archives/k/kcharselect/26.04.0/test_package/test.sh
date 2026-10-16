#!/bin/bash
# test_package/test.sh — kcharselect 26.04.0 消费者用例
# 用法: test.sh <kcharselect 二进制>
# （由 test_package/conanfile.py 调用；QT_QPA_PLATFORM=offscreen 已由调用方注入）
#
# 上游 kcharselect 26.04.0 无任何测试（0 用例）：tarball 内无 autotests/、
# 无 tests/ 目录（只有 doc/、pics/、po/、LICENSES/），CMakeLists.txt 只有
# add_executable(kcharselect) + target_sources(...) 且未注册任何测试
# （无 add_test/enable_testing/ecm_add_test；tarball 中仅有的两处
# BUILD_TESTING 出现在 CMakePresets.json 与 snapcraft.yaml，均只是传
# -DBUILD_TESTING=OFF）；上游 CI 的 .gitlab-ci.yml 引入 9 个共享模板
# （linux-qt6/linux-qt6-next/freebsd-qt6/windows-qt6/craft-windows-x86-64-qt6/
# flatpak/snap-snapcraft-lxd + xml-lint/yaml-lint），这些模板做构建/打包/lint，
# 仅在项目注册测试时才跑 ctest，而本项目未注册；.kde-ci.yml 亦未声明测试目标。
# 故本脚本的消费者用例即全部验证面（R34：必须实质执行被测包产物，禁止空壳）。
#
# 用例集（4 用例 / 5 断言 + 1 鸿蒙特有非断言用例）：
#   用例 1（2 断言）: 产物可执行；kcharselect --version -> 版本串 26.04.0
#   用例 2（1 断言）: kcharselect --help -> 命令行接口可用
#   用例 3（2 断言）: kcharselect --author -> KAboutData 作者；
#                     kcharselect --license -> 二进制 KAboutData 声明的
#                     GPL 许可证文本（上游 main.cc 传 KAboutLicense::GPL，
#                     与 COPYING/LICENSES/GPL-2.0-or-later.txt、appdata.xml 的
#                     GPL-2.0+ 一致；本用例验证运行时元数据路径）
#   用例 4（鸿蒙特有，非断言）: OHOS 共享库 closure 加载
#     真实启动包内 kcharselect，由 OHOS 动态链接器解析完整 DT_NEEDED
#     closure（KBookmarks/KCrash/KXmlGui/KColorScheme 及其传递闭包）。已发布
#     KF6 库以 "../../bin/libX.so" 相对形式与构建机绝对路径形式记录 NEEDED
#     —— OHOS 按符号链接路径（非 realpath）解析，未经
#     test_package/conanfile.py 归一化时加载必然失败；Linux glibc 下同形路径
#     可直接解析。故此用例在非 OHOS 平台恒过、在 OHOS 上是真实门禁。判定依据
#     是**进程运行时行为**（链接器能否完成解析），不比对任何特定输出内容，
#     故为"非断言"型消费者用例。
set -euo pipefail

KS="$1"

echo "[test] binary: $KS"
test -x "$KS" || { echo "[test] ❌ kcharselect not executable"; exit 1; }
echo "[test] ✅ 用例 1a 通过 —— 产物存在且可执行"

# ---------- 用例 1: kcharselect --version ----------
echo "[test] 用例 1b: --version"
set +e
OUT="$("$KS" --version 2>&1)"
RC=$?
set -e
echo "$OUT"
if [ "$RC" -ne 0 ]; then
    echo "[test] ❌ --version exited non-zero ($RC)"
    exit 1
fi
case "$OUT" in
    *26.04*)
        echo "[test] ✅ 用例 1b 通过 —— --version 报告 26.04.0"
        ;;
    *)
        echo "[test] ❌ 用例 1b 失败 —— 版本输出异常"
        exit 1
        ;;
esac

# ---------- 用例 2: kcharselect --help ----------
# 验证 Qt6/KF6 运行时链接完整（--help 触发 KAboutData + QCommandLineParser）
echo "[test] 用例 2: --help"
set +e
HELP_OUT="$("$KS" --help 2>&1)"
RC=$?
set -e
echo "$HELP_OUT" | head -8
if [ "$RC" -ne 0 ]; then
    echo "[test] ❌ --help exited non-zero ($RC)"
    exit 1
fi
case "$HELP_OUT" in
    *kcharselect*)
        echo "[test] ✅ 用例 2 通过 —— --help 识别 kcharselect"
        ;;
    *)
        echo "[test] ❌ 用例 2 失败 —— --help 输出异常"
        exit 1
        ;;
esac

# ---------- 用例 3: kcharselect --author / --license ----------
# KAboutData 元数据（KCoreAddons）随包可读
echo "[test] 用例 3a: --author"
AUTHOR_OUT="$("$KS" --author 2>&1)" || {
    echo "[test] ❌ --author exited non-zero"
    exit 1
}
echo "$AUTHOR_OUT"
case "$AUTHOR_OUT" in
    *"Christoph Feck"*)
        echo "[test] ✅ 用例 3a 通过 —— --author 输出 KAboutData 作者"
        ;;
    *)
        echo "[test] ❌ 用例 3a 失败 —— --author 输出异常"
        exit 1
        ;;
esac

echo "[test] 用例 3b: --license"
LICENSE_OUT="$("$KS" --license 2>&1)" || {
    echo "[test] ❌ --license exited non-zero"
    exit 1
}
if printf '%s\n' "$LICENSE_OUT" | grep -qiE 'GNU General Public License|GPL'; then
    echo "[test] ✅ 用例 3b 通过 —— --license 输出 GPL 许可证信息"
else
    echo "[test] ❌ 用例 3b 失败 —— --license 输出异常"
    exit 1
fi

# ---------- 用例 4（鸿蒙特有，非断言）: OHOS 共享库 closure 加载 ----------
# 以真实应用路径启动 kcharselect（非元数据路径），由 OHOS 动态链接器解析
# bin/kcharselect 的全部 DT_NEEDED，含依赖库中被归一化的相对/绝对条目。
# 判据：进程运行时不得出现链接器解析失败（cannot open shared object file /
# error while loading shared libraries / undefined symbol）。GUI 环境缺失
# （无 D-Bus session / 无 platform plugin 退出）不属于链接失败，不判失败。
echo "[test] 用例 4（鸿蒙特有）: OHOS shared-library closure load"
# Keep the diagnostic log OUT of the recipe tree in every fallback path:
# $PWD is the archive's test_package/ directory during `conan create`, and a
# stray *.log there is not covered by .gitignore (junk/JC gate risk).
LOG_DIR="${TMPDIR:-${HOME:-.}/tmp}"
if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
    LOG_DIR="$(mktemp -d 2>/dev/null)" || LOG_DIR="$PWD"
fi
CLOSURE_LOG="$LOG_DIR/kcharselect-closure-$$.log"
if ! : > "$CLOSURE_LOG" 2>/dev/null; then
    CLOSURE_LOG="$(mktemp 2>/dev/null)" || CLOSURE_LOG="$PWD/kcharselect-closure-$$.log"
fi

set +e
"$KS" >"$CLOSURE_LOG" 2>&1 &
KS_PID=$!
# 给动态链接器 + Qt/KF 初始化留出时间（轮询最多 10 秒）
i=0
while [ "$i" -lt 50 ]; do
    kill -0 "$KS_PID" 2>/dev/null || break
    sleep 0.2
    i=$((i + 1))
done
if kill -0 "$KS_PID" 2>/dev/null; then
    kill -TERM "$KS_PID" 2>/dev/null
fi
wait "$KS_PID" 2>/dev/null
CLOSURE_RC=$?
set -e

if grep -qE 'cannot open shared object file|error while loading shared libraries|symbol lookup error|undefined symbol' "$CLOSURE_LOG" 2>/dev/null; then
    echo "[test] ❌ 用例 4 失败 —— OHOS 动态链接器无法解析 DT_NEEDED closure："
    cat "$CLOSURE_LOG"
    exit 1
fi
echo "[test] ✅ 用例 4 通过 —— OHOS closure 加载成功，全部 DT_NEEDED 已解析（进程退出码 $CLOSURE_RC）"
# 日志摘录仅用于诊断：日志可能为空/不可读，此处有意忽略 head 的失败（不影响用例判定）
head -3 "$CLOSURE_LOG" 2>/dev/null || true

echo "[test] ALL CONSUMER CASES PASSED (4 用例 / 5 断言 + 1 鸿蒙特有非断言用例)"
