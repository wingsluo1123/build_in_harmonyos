#!/bin/bash
# test_package/test.sh — kdialog 26.04.0 消费者用例
# 用法: test.sh <kdialog 二进制>
# （由 test_package/conanfile.py 调用；QT_QPA_PLATFORM=offscreen 与
#   LD_LIBRARY_PATH/QT_PLUGIN_PATH 已由调用方注入。脚本全程不 chdir：
#   依赖制品中残留的相对 DT_NEEDED 条目由 CWD 解析，工作目录须保持为
#   conan test 的构建目录。助手二进制由 kdialog 二进制同目录推导。）
#
# 上游 kdialog 26.04.0 无任何注册测试（0 用例）：tests/ 目录仅 3 个
# 交互式演示 shell 脚本（tests/test 2879B、tests/progressdemo 426B、
# tests/progresscanceldemo 448B —— 需人工点击按钮或以 qdbus 驱动
# kdialog_progress_helper，非自动用例）；tests/ 下无 CMakeLists.txt、
# 顶层 CMakeLists.txt 未 add_subdirectory(tests)，脚本不在构建内；
# 全部 CMake 文件中递归查找 add_test/enable_testing/BUILD_TESTING/
# ecm_add_test/ctest 用法为空；.kde-ci.yml 声明 require-passing-tests-on:
# [Linux, FreeBSD] 却未注册任何测试目标；.gitlab-ci.yml 引入 7 个共享
# 模板，仅在项目注册测试时才执行 ctest。故本脚本的消费者用例即全部
# 验证面（R34：必须实质执行被测包产物，禁止空壳）。
#
# 用例集（5 用例 / 10 断言 + 1 鸿蒙特有用例 / 2 断言）：
#   用例 1（2 断言）: bin/kdialog 与 bin/kdialog_progress_helper 均存在可执行
#   用例 2（2 断言）: --version 退出 0 且报告 26.04.x 版本串
#   用例 3（2 断言）: --help 退出 0；帮助文本含 --passivepopup 与
#                     --progressbar（对话框选项面完整；两分支均依赖会话
#                     总线，有意不做端到端驱动——见配方 docstring）
#   用例 4（2 断言）: --author 输出 KAboutData 作者（David Faure）；
#                     --license 输出 GPL 许可证文本
#   用例 5（2 断言）: 未知选项失败路径——非零退出且打印 QCommandLineParser
#                     的 "Unknown option" 诊断（不得静默成功）
#   用例 6（鸿蒙特有，2 断言）:
#     6a: --msgbox 进入真实模态事件循环（KMessageBox::createKMessageBox +
#         QDialog::exec，kdialog.cpp）——3 秒宽限期内进程须存活，随后 TERM；
#         该用例同时门禁 kdialog 本体完整 DT_NEEDED closure 的加载。
#     6b: 包内 kdialog_progress_helper 直接启动，OHOS 动态链接器解析其完整
#         DT_NEEDED closure（有界等待后判定链接器解析失败字样）。两例判据
#         均为进程运行时行为而非输出文本；在 glibc 下恒过、在 OHOS 上是
#         真实门禁。
# R1 整改（2026-10-17 离线检视 #1）：原 `set -euo pipefail` 的 pipefail 非
# POSIX——调用方以 `sh test.sh` 执行（test_package/conanfile.py:383），dash 系
# 会在任何用例前报 "Illegal option -o pipefail" 退出；本脚本全部管道均为信息性
# 消费（head / if grep），删除后 `set -eu` 语义完整保留（真 POSIX）。
set -eu

KD="$1"
HELPER="$(dirname "$KD")/kdialog_progress_helper"

echo "[test] binary: $KD"
test -x "$KD" || { echo "[test] ❌ kdialog not executable"; exit 1; }
echo "[test] ✅ 用例 1a 通过 —— 产物 kdialog 存在且可执行"

if [ -x "$HELPER" ]; then
    echo "[test] ✅ 用例 1b 通过 —— kdialog_progress_helper 存在且可执行"
else
    echo "[test] ❌ 用例 1b 失败 —— 缺少可执行 kdialog_progress_helper: $HELPER"
    exit 1
fi

# ---------- 用例 2: kdialog --version ----------
echo "[test] 用例 2a: --version"
set +e
OUT="$("$KD" --version 2>&1)"
RC=$?
set -e
echo "$OUT"
if [ "$RC" -ne 0 ]; then
    echo "[test] ❌ 用例 2a 失败 —— --version 退出码 $RC"
    exit 1
fi
echo "[test] ✅ 用例 2a 通过 —— --version 退出 0"

echo "[test] 用例 2b: --version 报告 26.04 版本串"
case "$OUT" in
    *26.04*)
        echo "[test] ✅ 用例 2b 通过 —— 版本串含 26.04"
        ;;
    *)
        echo "[test] ❌ 用例 2b 失败 —— 版本输出异常"
        exit 1
        ;;
esac

# ---------- 用例 3: kdialog --help ----------
# 验证 Qt6/KF6 运行时链接完整（--help 触发 KAboutData + QCommandLineParser）
echo "[test] 用例 3a: --help"
set +e
HELP_OUT="$("$KD" --help 2>&1)"
RC=$?
set -e
printf '%s\n' "$HELP_OUT" | head -12
if [ "$RC" -ne 0 ]; then
    echo "[test] ❌ 用例 3a 失败 —— --help 退出码 $RC"
    exit 1
fi
echo "[test] ✅ 用例 3a 通过 —— --help 退出 0"

echo "[test] 用例 3b: --help 含 --passivepopup 与 --progressbar"
if printf '%s\n' "$HELP_OUT" | grep -q -- '--passivepopup' && \
   printf '%s\n' "$HELP_OUT" | grep -q -- '--progressbar'; then
    echo "[test] ✅ 用例 3b 通过 —— 对话框选项面完整（两个选项均已注册）"
else
    echo "[test] ❌ 用例 3b 失败 —— 帮助文本缺 --passivepopup 或 --progressbar"
    exit 1
fi

# ---------- 用例 4: kdialog --author / --license ----------
# KAboutData 元数据（KCoreAddons）随包可读
echo "[test] 用例 4a: --author"
AUTHOR_OUT="$("$KD" --author 2>&1)" || {
    echo "[test] ❌ 用例 4a 失败 —— --author 非零退出"
    exit 1
}
echo "$AUTHOR_OUT"
case "$AUTHOR_OUT" in
    *"David Faure"*)
        echo "[test] ✅ 用例 4a 通过 —— --author 输出上游作者"
        ;;
    *)
        echo "[test] ❌ 用例 4a 失败 —— --author 输出异常"
        exit 1
        ;;
esac

echo "[test] 用例 4b: --license"
LICENSE_OUT="$("$KD" --license 2>&1)" || {
    echo "[test] ❌ 用例 4b 失败 —— --license 非零退出"
    exit 1
}
if printf '%s\n' "$LICENSE_OUT" | grep -qiE 'General Public License|GNU'; then
    echo "[test] ✅ 用例 4b 通过 —— --license 输出 GPL 许可证文本"
else
    echo "[test] ❌ 用例 4b 失败 —— --license 输出异常"
    exit 1
fi

# ---------- 用例 5: 未知选项失败路径 ----------
echo "[test] 用例 5a: 未知选项 -> 非零退出"
set +e
UNKNOWN_OUT="$("$KD" --definitely-not-a-kdialog-option 2>&1)"
UNKNOWN_RC=$?
set -e
printf '%s\n' "$UNKNOWN_OUT" | head -5
if [ "$UNKNOWN_RC" -eq 0 ]; then
    echo "[test] ❌ 用例 5a 失败 —— 未知选项却退出 0"
    exit 1
fi
echo "[test] ✅ 用例 5a 通过 —— 未知选项非零退出（$UNKNOWN_RC）"

echo "[test] 用例 5b: 打印 Unknown option 诊断"
case "$UNKNOWN_OUT" in
    *"Unknown option"*)
        echo "[test] ✅ 用例 5b 通过 —— QCommandLineParser 失败诊断在"
        ;;
    *)
        echo "[test] ❌ 用例 5b 失败 —— 缺少 'Unknown option' 诊断"
        exit 1
        ;;
esac

# ---------- 用例 6（鸿蒙特有）: 模态事件循环 + 助手闭包加载 ----------
# 可写日志目录多级兜底（R1 整改 2026-10-17 离线检视 #4，kcharselect 26.04.0
# 先例）：$TMPDIR -> $HOME/tmp 建目录失败 -> mktemp -d -> $PWD；日志文件本身
# 也走 mktemp 兜底，避免失败时 *.log 落进归档目录（OHOS 真机 /tmp 只读）。
LOG_DIR="${TMPDIR:-${HOME:-.}/tmp}"
if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
    LOG_DIR="$(mktemp -d 2>/dev/null)" || LOG_DIR="$PWD"
fi

echo "[test] 用例 6a（鸿蒙特有）: --msgbox 模态事件循环存活（3s 宽限）"
MSG_LOG="$LOG_DIR/kdialog-msgbox-$$.log"
if ! : > "$MSG_LOG" 2>/dev/null; then
    MSG_LOG="$(mktemp 2>/dev/null)" || MSG_LOG="$PWD/kdialog-msgbox-$$.log"
fi
set +e
"$KD" --msgbox "kdialog consumer probe" >"$MSG_LOG" 2>&1 &
KD_PID=$!
ALIVE=1
i=0
while [ "$i" -lt 15 ]; do
    if ! kill -0 "$KD_PID" 2>/dev/null; then
        ALIVE=0
        break
    fi
    sleep 0.2
    i=$((i + 1))
done
if [ "$ALIVE" -eq 1 ]; then
    kill -TERM "$KD_PID" 2>/dev/null
fi
wait "$KD_PID" 2>/dev/null
MSG_RC=$?
set -e
if [ "$ALIVE" -ne 1 ]; then
    echo "[test] ❌ 用例 6a 失败 —— --msgbox 未存活过 3 秒宽限（退出码 $MSG_RC）"
    tail -20 "$MSG_LOG" 2>/dev/null || true
    exit 1
fi
echo "[test] ✅ 用例 6a 通过 —— --msgbox 模态事件循环存活（宽限后仍在运行，已 TERM）"

echo "[test] 用例 6b（鸿蒙特有）: kdialog_progress_helper 直接启动（DT_NEEDED closure 加载）"
HP_LOG="$LOG_DIR/kdialog-helper-$$.log"
if ! : > "$HP_LOG" 2>/dev/null; then
    HP_LOG="$(mktemp 2>/dev/null)" || HP_LOG="$PWD/kdialog-helper-$$.log"
fi
set +e
"$HELPER" >"$HP_LOG" 2>&1 &
HP_PID=$!
i=0
while [ "$i" -lt 25 ]; do
    if ! kill -0 "$HP_PID" 2>/dev/null; then
        break
    fi
    sleep 0.2
    i=$((i + 1))
done
if kill -0 "$HP_PID" 2>/dev/null; then
    kill -TERM "$HP_PID" 2>/dev/null
fi
wait "$HP_PID" 2>/dev/null
HP_RC=$?
set -e
if grep -qE 'cannot open shared object file|error while loading shared libraries|symbol lookup error|undefined symbol' "$HP_LOG" 2>/dev/null; then
    echo "[test] ❌ 用例 6b 失败 —— OHOS 动态链接器无法解析 kdialog_progress_helper 的 DT_NEEDED closure："
    cat "$HP_LOG"
    exit 1
fi
echo "[test] ✅ 用例 6b 通过 —— helper 闭包加载成功（进程退出码 $HP_RC，无链接器解析失败）"
# 日志摘录仅用于诊断：日志可能为空/不可读，此处有意忽略 head 的失败（不影响用例判定）
head -3 "$HP_LOG" 2>/dev/null || true

echo "[test] ALL CONSUMER CASES PASSED (5 用例 / 10 断言 + 1 鸿蒙特有用例 / 2 断言)"
