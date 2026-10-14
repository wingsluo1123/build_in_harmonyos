#!/usr/bin/env bash
# test_package/test_scribus.sh — scribus 1.6.6 消费者测试
#
# 真实 exec 被测包安装的 scribus GUI 可执行文件（L0c 测试源 / L0d self.run /
# R34 实质依赖被测包），断言落在被测二进制的真实进程输出上。
#
# 上游命令行契约（源码级核对，v1.6.6）：
#   * scribusapp.cpp 定义 ARG_VERSION "--version"，在进入 Qt 事件循环之前
#     处理（版本打印后退出），故 headless 下可安全断言 --version 输出。
#
# 无头环境：QT_QPA_PLATFORM=offscreen（qt5-qtbase 制品含 libqoffscreen.so）。
# libc++_shared.so 位于 OHOS SDK 的按架构分层 llvm lib 目录，此处补齐
# （qastools 同款处置；SDK 版本用通配符发现）。
#
# 用法: test_scribus.sh <bin-dir>      （由 test_package/conanfile.py 调用）
set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "[fail] usage: $0 <bin-dir>   (got: '${1:-}')" >&2
    exit 2
fi

# ── 运行环境准备 ────────────────────────────────────────────────────
# D15：OHOS aarch64 的 /tmp 只读，临时文件一律落 $HOME/tmp 并先建目录。
if [ -z "${TMPDIR:-}" ]; then
    export TMPDIR="${HOME}/tmp"
    mkdir -p "$TMPDIR"
fi

# libc++_shared.so：按架构分层的 SDK llvm lib 目录（可用 OHOS_SDK_LLVM_LIB 覆盖）。
if [ -z "${OHOS_SDK_LLVM_LIB:-}" ]; then
    for _d in /data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/aarch64-linux-ohos; do
        if [ -d "$_d" ]; then
            OHOS_SDK_LLVM_LIB="$_d"
        fi
    done
fi
if [ -n "${OHOS_SDK_LLVM_LIB:-}" ] && [ -d "$OHOS_SDK_LLVM_LIB" ]; then
    # scribus DT_NEEDED is libc++_shared.so (c++ subdir). Do NOT prepend the
    # SDK root dir: its libc++.so is a stub that breaks symbol resolution of
    # system libs (/system/lib64/libhilog_inner.so etc). Only c++ subdir.
    _sdk_cxx="$OHOS_SDK_LLVM_LIB/c++"
    if [ -d "$_sdk_cxx" ]; then
        # scribus/Qt5 need libc++_shared.so (c++ subdir); system libs
        # (libhilog_inner etc.) need libc++.so which must NOT resolve to the
        # SDK root 20-byte stub -- put /system/lib64 ahead of any stub path.
        export LD_LIBRARY_PATH="$_sdk_cxx:/system/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
        echo "[ok]   SDK libc++_shared.so + /system/lib64 prepended"
    else
        echo "[warn] SDK c++ subdir not found; libc++_shared.so may be unresolvable"
    fi
else
    echo "[warn] SDK per-arch llvm lib not discovered; libc++_shared.so may be unresolvable"
fi

# Qt5 runtime libs (Qt5Core/Qt5Widgets/Qt5Gui/...) live in the conan
# qt5-qtbase package prefix; prepend them so scribus can dlopen them.
if [ -z "${QT5_LIB_DIR:-}" ]; then
    for _d in "${HOME}"/.conan2/p/qt5-*/p/lib; do
        if [ -d "$_d" ]; then
            QT5_LIB_DIR="$_d"
        fi
    done
fi
if [ -n "${QT5_LIB_DIR:-}" ] && [ -d "$QT5_LIB_DIR" ]; then
    export LD_LIBRARY_PATH="$QT5_LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    echo "[ok]   Qt5 lib dir prepended: $QT5_LIB_DIR"
else
    echo "[warn] Qt5 lib dir not discovered; scribus --version may fail to dlopen Qt5"
fi

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
echo "[ok]   QT_QPA_PLATFORM=$QT_QPA_PLATFORM"
# Qt platform plugins (libqoffscreen.so etc.) live under the conan
# qt5-qtbase package plugins dir; QT_PLUGIN_PATH must point there so the
# offscreen platform can be loaded headlessly.
if [ -z "${QT_PLUGIN_PATH:-}" ]; then
    for _d in "${HOME}"/.conan2/p/qt5-*/p/plugins; do
        if [ -d "$_d" ]; then
            QT_PLUGIN_PATH="$_d"
        fi
    done
fi
if [ -n "${QT_PLUGIN_PATH:-}" ] && [ -d "$QT_PLUGIN_PATH" ]; then
    export QT_PLUGIN_PATH="$QT_PLUGIN_PATH"
    echo "[ok]   QT_PLUGIN_PATH=$QT_PLUGIN_PATH"
else
    echo "[warn] Qt plugins dir not discovered; offscreen platform may fail"
fi
echo "[ok]   TMPDIR=$TMPDIR"

RUN_TIMEOUT="${SCRIBUS_TEST_TIMEOUT:-15}"
PASS=0
FAIL=0
OUT=""
RC=0

ok()   { echo "[ok]   $*"; PASS=$((PASS + 1)); }
bad()  { echo "[fail] $*"; FAIL=$((FAIL + 1)); }

# 期望非零退出的调用统一走这里：set -e 会因命令替换非零而中止，故显式关/开。
run_cli() {
    set +e
    OUT=$(timeout "$RUN_TIMEOUT" "$@" 2>&1)
    RC=$?
    set -e
}

# 纯 bash 读 ELF 魔数（不依赖 file/od/dd —— OHOS CI 的 coreutils 覆盖不稳定）
elf_magic() {
    local magic=""
    if ! IFS= read -r -n 4 magic < "$1"; then
        magic=""
    fi
    [ "$magic" = $'\177ELF' ]
}

# 失败时给出可定位的诊断，避免下一轮只能看到"红"
diagnose() {
    case "$1" in
        *"Error loading shared library"*|*"cannot open shared object file"*)
            echo "       hint: 动态链接闭包不完整——核对 conanrun 的 LD_LIBRARY_PATH 是否覆盖 Qt5 各 .so" ;;
        *"failed to start because no Qt platform plugin"*|*"could not load the Qt platform plugin"*)
            echo "       hint: Qt 平台插件缺失——确认 qt5-qtbase 制品含 offscreen 插件" ;;
        *"Permission denied"*)
            echo "       hint: HMDFS 上 exec 权限受限——参考 qastools/fceux 配方：拷到可写 TMPDIR 后自签再 exec" ;;
    esac
}

# ── 1. scribus 可执行文件存在、可执行、是 ELF ────────────────────────
echo "[step] installed executable"
bin="$BIN_DIR/scribus"
if [ ! -f "$bin" ]; then
    bad "scribus missing: $bin"
    echo "RESULT: $PASS passed, $FAIL failed"
    exit 1
fi
ok "scribus installed"
if [ -x "$bin" ]; then
    ok "scribus executable bit"
else
    bad "scribus not executable"
fi
if elf_magic "$bin"; then
    ok "scribus ELF magic"
else
    bad "scribus not an ELF object"
fi

# ── 2. scribus --version：打印版本信息后退出，不进事件循环 ───────────
echo "[step] scribus --version (expect version banner)"
if [ -x "$bin" ]; then
    run_cli "$bin" --version
    echo "$OUT" | head -n 20
    echo "[info] scribus --version rc=$RC"
    case "$OUT" in
        *"1.6.6"*|*"Scribus"*)
            ok "scribus --version reports version info"
            ;;
        *)
            bad "scribus --version output does not contain version banner"
            diagnose "$OUT"
            ;;
    esac
fi

TOTAL=$((PASS + FAIL))
echo ""
echo "RESULT: $PASS passed, $FAIL failed"
if [ "$TOTAL" -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"test_scribus.sh\",\"discovered\":0,\"passedCount\":0}"
    echo "test_scribus.sh: no case executed — harness broken" >&2
    exit 1
fi
if [ "$FAIL" -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"test_scribus.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASS}"
    exit 0
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"test_scribus.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASS}"
exit 1
