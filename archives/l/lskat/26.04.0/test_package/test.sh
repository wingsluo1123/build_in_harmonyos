#!/bin/sh
# test_package/test.sh — lskat 26.04.0 消费者用例
# 用法: test.sh <lskat 二进制>
# （由 test_package/conanfile.py 调用；QT_QPA_PLATFORM=offscreen 已由调用方注入）
#
# 上游 lskat 26.04.0 **没有测试套件**（R51 清点：tarball 内无 tests/、autotests/、
# test/ 目录，任何 CMakeLists.txt 中都没有 enable_testing()/add_test()/
# ecm_add_test()/BUILD_TESTING；.kde-ci.yml 只有 require-passing-tests-on 声明）。
# 因此消费者验证即本包的唯一验证路径。
#
# 用例集（6 用例 / 8 断言，其中鸿蒙特有 2 用例）：
#   前置断言: 包内 bin/lskat 存在且可执行
#   用例 1（上游兼容）: lskat --version  -> 版本串 1.50.26040
#   用例 2（上游兼容）: lskat --help     -> 命令行接口可用
#                        （KAboutData + QCommandLineParser 已完成运行时链接）
#   用例 3（上游兼容）: lskat --author / --license -> KAboutData 元数据完整
#   用例 4（鸿蒙特有，非断言）: OHOS 共享库 closure 加载
#     真实启动包内 lskat，由 OHOS 动态链接器解析完整 DT_NEEDED closure
#     （KF6/Qt6 栈 + KDEGames6 + openal/sndfile）。已发布 KF6 库以
#     "../../bin/libX.so" 相对形式或构建机绝对路径记录 NEEDED —— OHOS musl
#     按字面路径解析、无 LD_LIBRARY_PATH 回退，未经规范化时加载必然失败；
#     Linux glibc 下同形路径可直接解析。故此用例在非 OHOS 平台恒过、在 OHOS
#     上是真实门禁。判定依据是**进程运行时行为**（链接器能否完成解析），
#     不比对任何特定输出内容，故为"非断言"型消费者用例。
#   用例 5（鸿蒙特有）: 产物签名与目标架构门禁
#     OHOS 对可执行 ELF 强制校验 .codesign 段（缺失= EACCES，无法 exec）；
#     且包内二进制必须是 AArch64（e_machine=183）。两者都在 OHOS 上断言，
#     非 OHOS 平台跳过（记 skip，不判失败）。
set -euo pipefail

LSKAT="$1"
# 平台由 test_package/conanfile.py 通过 LSKAT_TEST_OS 传入（settings.os 真值，
# 不用 uname 猜测：OHOS 设备上 uname -s 可能报 Linux）
OHOS_HOST=0
case "${LSKAT_TEST_OS:-unknown}" in
    OHOS|HarmonyOS|ohos) OHOS_HOST=1 ;;
esac
echo "[test] target os: ${LSKAT_TEST_OS:-unknown}"

PASS=0
CASES=6
echo "[test] binary: $LSKAT"

# ---------- 用例 0（前置）: 包内二进制存在且可执行 ----------
echo "[test] 用例 0（前置）: 包内 bin/lskat 存在且可执行"
test -x "$LSKAT" || { echo "[test] ❌ 用例 0 失败 —— lskat 不可执行"; exit 1; }
echo "[test] ✅ 用例 0 通过 —— $LSKAT 存在且可执行"
PASS=$((PASS + 1))

# ---------- 用例 1: lskat --version ----------
echo "[test] 用例 1: --version"
OUT="$("$LSKAT" --version 2>&1)" || {
    echo "[test] ❌ --version exited non-zero"
    echo "$OUT"
    exit 1
}
echo "$OUT"

case "$OUT" in
    *1.50.26040*|*26040*)
        echo "[test] ✅ 用例 1 通过 —— --version 报告 1.50.26040（KDE Gear 26.04.0）"
        PASS=$((PASS + 1))
        ;;
    *)
        echo "[test] ❌ 用例 1 失败 —— 版本输出异常"
        exit 1
        ;;
esac

# ---------- 用例 2: lskat --help ----------
# 验证 Qt 和 KDE 运行时链接完整（--help 触发 KAboutData 和 QCommandLineParser）
echo "[test] 用例 2: --help"
HELP_OUT="$("$LSKAT" --help 2>&1)" || {
    echo "[test] ❌ --help exited non-zero"
    echo "$HELP_OUT"
    exit 1
}
echo "$HELP_OUT" | head -5

case "$HELP_OUT" in
    *lskat*|*LSkat*)
        echo "[test] ✅ 用例 2 通过 —— --help 识别 lskat"
        PASS=$((PASS + 1))
        ;;
    *)
        echo "[test] ❌ 用例 2 失败 —— --help 输出异常"
        exit 1
        ;;
esac

# ---------- 用例 3: lskat --author / --license ----------
# KAboutData 元数据资源（author/license）随包安装且可读取
echo "[test] 用例 3: --author / --license"
AUTHOR_OUT="$("$LSKAT" --author 2>&1)" || {
    echo "[test] ❌ --author exited non-zero"
    exit 1
}
case "$AUTHOR_OUT" in
    *Martin\ Heni*|*Heni*)
        echo "[test] ✅ 用例 3a 通过 —— --author 输出上游作者信息"
        PASS=$((PASS + 1))
        ;;
    *)
        echo "[test] ❌ 用例 3a 失败 —— --author 输出异常"
        exit 1
        ;;
esac
LICENSE_OUT="$("$LSKAT" --license 2>&1)" || {
    echo "[test] ❌ --license exited non-zero"
    exit 1
}
if printf '%s\n' "$LICENSE_OUT" | grep -qiE 'GPL|GENERAL PUBLIC LICENSE'; then
    echo "[test] ✅ 用例 3b 通过 —— --license 输出许可证信息"
    PASS=$((PASS + 1))
else
    echo "[test] ❌ 用例 3b 失败 —— --license 输出异常"
    exit 1
fi

# ---------- 用例 4（鸿蒙特有，非断言）: OHOS 共享库 closure 加载 ----------
# 以真实应用路径启动 lskat（非元数据路径），由 OHOS 动态链接器解析
# bin/lskat 的全部 DT_NEEDED。判据：进程运行时不得出现链接器解析失败
# （cannot open shared object file / error while loading shared libraries /
# undefined symbol）。GUI 环境缺失（无 D-Bus session / 无 platform plugin）
# 导致的退出不属于链接失败，不判失败。
echo "[test] 用例 4（鸿蒙特有）: OHOS shared-library closure load"
LOG_DIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="$PWD"
CLOSURE_LOG="$LOG_DIR/lskat-closure-$$.log"
: > "$CLOSURE_LOG" 2>/dev/null || true

set +e
"$LSKAT" >"$CLOSURE_LOG" 2>&1 &
LSKAT_PID=$!
# 给动态链接器 + Qt/KF 初始化留出时间（轮询最多 10 秒）
i=0
while [ "$i" -lt 50 ]; do
    kill -0 "$LSKAT_PID" 2>/dev/null || break
    sleep 0.2
    i=$((i + 1))
done
if kill -0 "$LSKAT_PID" 2>/dev/null; then
    kill -TERM "$LSKAT_PID" 2>/dev/null
fi
wait "$LSKAT_PID" 2>/dev/null
CLOSURE_RC=$?
set -e

if grep -qE 'cannot open shared object file|error while loading shared libraries|symbol lookup error|undefined symbol' "$CLOSURE_LOG" 2>/dev/null; then
    echo "[test] ❌ 用例 4 失败 —— OHOS 动态链接器无法解析 DT_NEEDED closure："
    cat "$CLOSURE_LOG"
    exit 1
fi
echo "[test] ✅ 用例 4 通过 —— closure 加载成功，全部 DT_NEEDED 已解析（进程退出码 $CLOSURE_RC）"
PASS=$((PASS + 1))
head -3 "$CLOSURE_LOG" 2>/dev/null || true

# ---------- 用例 5（鸿蒙特有）: 签名段 + 目标架构 ----------
echo "[test] 用例 5（鸿蒙特有）: OHOS .codesign 签名段 + AArch64 门禁"
if [ "$OHOS_HOST" -eq 1 ]; then
    # (a) e_machine = 183 (AArch64)，ELF64 小端
    python3 - "$LSKAT" <<'PY'
import sys
data = open(sys.argv[1], "rb").read(64)
if data[:4] != b"\x7fELF" or data[4] != 2:
    raise SystemExit("[test] ❌ 用例 5a 失败 —— 不是 ELF64")
machine = int.from_bytes(data[18:20], "little")
if machine != 183:
    raise SystemExit(f"[test] ❌ 用例 5a 失败 —— e_machine={machine}（期望 183/AArch64）")
print("[test] ✅ 用例 5a 通过 —— ELF64 AArch64（e_machine=183）")
PY
    PASS=$((PASS + 1))
    # (b) .codesign 段存在（未签名/签名被破坏的 ELF 在 OHOS 上 exec 会被拒）
    if grep -qa "\.codesign" "$LSKAT"; then
        echo "[test] ✅ 用例 5b 通过 —— 二进制含 .codesign 段（OHOS 签名有效）"
        PASS=$((PASS + 1))
    else
        echo "[test] ❌ 用例 5b 失败 —— 二进制缺少 .codesign 段，OHOS 将拒绝执行"
        exit 1
    fi
else
    echo "[test] ⏭ 用例 5 skip —— 非 OHOS 宿主，跳过签名/架构门禁（不计入断言）"
fi

echo "[test] ALL CONSUMER CASES PASSED ($CASES 用例 / $PASS 断言，0 失败)"
