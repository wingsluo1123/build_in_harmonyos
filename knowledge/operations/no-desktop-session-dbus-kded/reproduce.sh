#!/bin/sh
# reproduce.sh — 干净环境复现本主题的两条断言：**关策略报错 → 开策略生效**
#
# 演示对象 = sample/（kwrited 6.7.2 双分支结构的去业务化最小复刻）
#   「关策略」= SAMPLE_ASSUME_DESKTOP_SESSION=1（即假装本平台有桌面会话 / utempter / KDED）
#              → 样例把 BUILD_AS_EXECUTABLE 钉为 OFF → 进入会话插件分支，
#                find_package(KF6DBusAddons ... REQUIRED) 失败 → 配置报错
#   「开策略」= 默认配置 → KF6Pty 包导出的 KPty_HAVE_UTEMPTER=FALSE 通过
#              cmake_dependent_option 强制 BUILD_AS_EXECUTABLE=ON
#              → 独立可执行分支，配置 + 编译 + 运行全部通过
#
# 构建走 conan（与 CI/W3 同机制），不手搓 cmake 命令行：依赖前缀由 sample/conanfile.py
# 的 generate() 手工写入 conan_cmakedeps_paths.cmake（本仓库 KF6/Qt6 配方用
# cmake_find_mode=none，CMakeDeps 不会生成该文件，kpty 6.26.0 / kwrited 6.7.2 先例）。
#
# 用法:
#   sh reproduce.sh                      # 使用仓库内 OHOS aarch64 profile
#   OHC_CONAN_PROFILE=/path/to/profile sh reproduce.sh
#   OHC_CONAN_REMOTE=ohpcd sh reproduce.sh
#
# 前置（干净环境）:
#   - conan 2.x 可用；制品仓可访问（qtbase/6.11.1、kcoreaddons/6.26.0.1、ki18n/6.26.0、ecm/6.26.0）
#   - kpty/6.26.0 可用：制品仓已发布（前置 PR：【依赖项】feat(kpty): 6.26.0 适配完成 = #15405，
#     合入发布后即可），或本机 conan cache 已有该包（`conan create archives/k/kpty/6.26.0`）
# 说明:
#   - 不复用任何本地构建产物：两个变体各用私有输出目录，每轮清空；
#   - 不写死任何本地绝对路径：仓库根由脚本自身位置推导，profile/remote 均可覆盖；
#   - 安全模式按规范（code-style 规则 7）：`-e` 生效，对“预期非零”的命令逐个显式兜底（见行内注释），
#     管道末端统一用 sed 而非 head，避免上游被 SIGPIPE 误杀触发 -e 提前退出。
set -eu -o pipefail

SELF_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SELF_DIR/../../.." && pwd)
SAMPLE_DIR="$SELF_DIR/sample"
WORK="${OHC_DEMO_DIR:-${TMPDIR:-.}/session-strategy-demo}"
PROFILE="${OHC_CONAN_PROFILE:-$REPO_ROOT/ci/conan/profiles/ohos-aarch64}"
CONAN="${CONAN:-conan}"
REMOTE="${OHC_CONAN_REMOTE:-ohpcd}"

say() { printf '%s\n' "$*"; }
RC=0

say "== 无桌面会话策略样例：关策略报错 / 开策略生效 =="
say "repo    = $REPO_ROOT"
say "work    = $WORK  (每次运行前清空)"
say "profile = $PROFILE"
say "remote  = $REMOTE"
say "conan   = $($CONAN --version 2>/dev/null | sed -n '1p' || true)"   # conan 缺失时留空，由后续 conan 调用报错

if [ ! -f "$PROFILE" ]; then
    say "FAIL: conan profile 不存在: $PROFILE"
    exit 2
fi
if [ ! -f "$SAMPLE_DIR/conanfile.py" ]; then
    say "FAIL: 样例配方不存在: $SAMPLE_DIR/conanfile.py"
    exit 2
fi

rm -rf "$WORK"
mkdir -p "$WORK"

CONAN_ARGS="-pr:h=$PROFILE -pr:b=$PROFILE -s:h build_type=Release -s:b build_type=Release -r=$REMOTE"
# shellcheck disable=SC2086
install_variant() {
    # $1 = 变体名（off/on）
    "$CONAN" install "$SAMPLE_DIR" -of "$WORK/$1" $CONAN_ARGS \
        > "$WORK/install-$1.log" 2>&1
}

# ---- [1/4] 干净依赖 ---------------------------------------------------------
say ""
say "-- [1/4] conan install（两个变体各自私有输出目录，不复用本地产物）"
for v in off on; do
    if ! install_variant "$v"; then
        say "FAIL: conan install 失败（变体 $v）—— 先补齐前置依赖（kpty/6.26.0 需先发布）"
        tail -n 15 "$WORK/install-$v.log" | sed 's/^/    /'
        exit 1
    fi
done
GEN_OFF="$WORK/off/build/Release/generators"
GEN_ON="$WORK/on/build/Release/generators"
if [ ! -f "$GEN_ON/conan_toolchain.cmake" ]; then
    say "FAIL: 未生成 CMakeToolchain: $GEN_ON/conan_toolchain.cmake"
    exit 1
fi
if [ ! -f "$GEN_ON/conan_cmakedeps_paths.cmake" ]; then
    say "FAIL: 未生成 conan_cmakedeps_paths.cmake（样例 generate() 未生效）"
    exit 1
fi
say "OK: 依赖就绪（两变体），toolchain = $GEN_ON/conan_toolchain.cmake"

# 运行期库路径：从 generate() 写出的依赖库目录推导，外加 OHOS 系统库目录
# （/system/lib64 前置，避免沙箱内 libc++_shared.so 被遮蔽）。
LIB_DIRS=$(grep -oE 'CMAKE_LIBRARY_PATH "[^"]+"' "$GEN_ON/conan_cmakedeps_paths.cmake" 2>/dev/null \
    | sed 's/.*"\(.*\)"/\1/' | tr '\n' ':' || true)   # 无匹配时留空：运行期退回只加 OHOS 系统库目录
RUN_LD="/system/lib64:${LIB_DIRS}${LIB_DIRS:+}$WORK/on/build/Release"

# ---- [2/4] 关策略：必须报错 -------------------------------------------------
say ""
say "-- [2/4] 关策略：SAMPLE_ASSUME_DESKTOP_SESSION=1（假装有桌面会话 → 走 KDED 插件分支）"
if SAMPLE_ASSUME_DESKTOP_SESSION=1 "$CONAN" build "$SAMPLE_DIR" -of "$WORK/off" $CONAN_ARGS \
        > "$WORK/build-off.log" 2>&1; then
    say "FAIL: 关策略竟然构建成功 —— 样例未复现出会话插件分支的硬依赖（预期 find_package(KF6DBusAddons REQUIRED) 报错）"
    RC=1
else
    if grep -q 'KF6DBusAddons' "$WORK/build-off.log"; then
        say "OK: 关策略按预期在配置阶段报错，证据："
        grep -m 2 'KF6DBusAddons' "$WORK/build-off.log" | sed 's/^[[:space:]]*/    /'
    else
        say "FAIL: 关策略确实失败，但原因不是会话插件分支的 KF6DBusAddons 硬依赖（假阳性，不能算证据）"
        grep -m 1 -E 'CMake Error|ERROR' "$WORK/build-off.log" 2>/dev/null \
            | sed 's/^[[:space:]]*/    /' || true   # 无匹配属正常（下一步照旧判 FAIL），不让 -e 打断
        RC=1
    fi
fi

# ---- [3/4] 开策略：必须生效 -------------------------------------------------
say ""
say "-- [3/4] 开策略：默认配置（KPty_HAVE_UTEMPTER=FALSE → 强制可执行分支）"
if ! "$CONAN" build "$SAMPLE_DIR" -of "$WORK/on" $CONAN_ARGS \
        > "$WORK/build-on.log" 2>&1; then
    say "FAIL: 开策略构建失败"
    tail -n 15 "$WORK/build-on.log" | sed 's/^/    /'
    exit 1
fi
CFG_LINE=$(grep -m 1 'session-strategy sample:' "$WORK/build-on.log" || true)
printf '%s\n' "$CFG_LINE" | sed 's/^[[:space:]]*/    /'
say "OK: 开策略配置 + 编译通过"
case "$CFG_LINE" in
    *KPty_HAVE_UTEMPTER=FALSE*BUILD_AS_EXECUTABLE=ON*)
        say "OK: 形态判定来源已实证（KF6Pty 导出 KPty_HAVE_UTEMPTER=FALSE → cmake_dependent_option 强制 BUILD_AS_EXECUTABLE=ON）"
        ;;
    *)
        say "FAIL: 未从配置输出取到 KPty_HAVE_UTEMPTER=FALSE + BUILD_AS_EXECUTABLE=ON（形态判定未被证实）"
        RC=1
        ;;
esac

# ---- [4/4] 产物形态与运行证据 ----------------------------------------------
say ""
say "-- [4/4] 产物形态与运行证据"
ON_BIN="$WORK/on/build/Release/session_strategy_sample"
if [ -f "$ON_BIN" ]; then
    say "OK: 产物为独立可执行文件（开策略分支）build/Release/session_strategy_sample"
else
    say "FAIL: 期望的独立可执行产物不存在（形态判定错误）"
    RC=1
fi

if [ -f "$ON_BIN" ]; then
    # shellcheck disable=SC2086
    if OUT=$(LD_LIBRARY_PATH="$RUN_LD" timeout 20 "$ON_BIN" 2>&1); then
        say "OK: 无桌面会话（无 D-Bus 会话总线、无 KDED）下运行成功，输出："
        printf '%s\n' "$OUT" | sed -n '1,4p' | sed 's/^[[:space:]]*/    /'
        case "$OUT" in
            *branch=executable*pty_open=true*)
                say "OK: 实跑证据已断言（可执行分支 + pty 打开成功）"
                ;;
            *)
                say "FAIL: 运行输出缺少 branch=executable / pty_open=true（pty 未真正打开）"
                RC=1
                ;;
        esac
    else
        say "FAIL: 开策略产物运行失败（策略应在无会话总线的环境下照常工作）"
        printf '%s\n' "${OUT:-}" | sed -n '1,6p' | sed 's/^[[:space:]]*/    /'
        RC=1
    fi
fi

say ""
if [ "$RC" -eq 0 ]; then
    say "RESULT: PASS —— 关策略=配置报错（预期） / 开策略=配置+编译+运行成功（预期）"
else
    say "RESULT: FAIL —— 见上方 FAIL 行"
fi
exit "$RC"
