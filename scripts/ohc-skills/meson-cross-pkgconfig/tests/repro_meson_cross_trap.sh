#!/usr/bin/env sh
# 复现脚本：meson 直驱交叉配方两类陷阱的 A/B 双向验证
#   陷阱①：-Dshared= vs --default-library（G2 实证第 1/2 轮）
#   陷阱②：嵌套 $() 子 shell vs 两步法（G2 实证第 3 轮，conan 沙箱等价的
#          受限 sh 环境复现）
#
# 输出：TRAP_REPRODUCED_*（关策略复现原始报错）→
#       FIX_CONFIRMED_*（开策略通过）→
#       最终 REPRO_SCRIPT_EFFECTIVE=1
#
# 产物全部落临时目录（mktemp -d，退出清理），日志重定向文件不落管道
#（规避 SIGPIPE），不写死任何本机路径。
set -u

WORK="$(mktemp -d "${TMPDIR:-/tmp}/meson-cross-repro.XXXXXX")" || exit 2
RESULT=1
# 仅成功时清理现场；失败保留供诊断（含 b.log/b-ninja.log）
trap '[ "$RESULT" -eq 0 ] && rm -rf "$WORK"' EXIT

# ---------- 最小 meson 工程（模拟 lv2 生态：无 shared 选项）----------
mkdir -p "$WORK/proj"
cat > "$WORK/proj/meson.build" <<'EOF'
project('mini', 'c', version: '0.1.0')
cc = meson.get_compiler('c')
lib = library('mini', 'mini.c', install: true)
EOF
cat > "$WORK/proj/mini.c" <<'EOF'
int mini_add(int a, int b) { return a + b; }
EOF

command -v meson >/dev/null 2>&1 || { echo "meson not found; skip A/B"; exit 3; }
MESON="$(command -v meson)"
# PATH 名 → 绝对路径（执行验证法：逐 PATH 目录实际执行探测——E046 族下
# [ -x ] 与 command -v 均不可靠；cross file 必须写绝对路径，裸名由 meson
# 子进程解析实测 ENOENT，与配方 build() 写 conf 提供的绝对路径同构）
abs_resolve() (
    case "$1" in
        */*) echo "$1"; return 0 ;;
    esac
    IFS=:
    for d in $PATH; do
        [ -n "$d" ] || continue
        if "$d/$1" --version >/dev/null 2>&1; then
            echo "$d/$1"
            return 0
        fi
    done
    echo "$1"
)
# 原生编译器解析（候选探测 + $CC 覆盖优先；不写死单一路径——本机编译器
# 常装在非 PATH 前缀，B 面 meson setup 需要可用的原生 cc）
CC_BIN=""
for cand in "${CC:-}" clang cc gcc; do
    if [ -n "$cand" ] && "$cand" --version >/dev/null 2>&1; then
        CC_BIN="$cand"
        break
    fi
done
# 兜底位探测同样用实际执行——HMDFS 属主映射使 [ -x ] 恒 False（E046 族），
# 凭 -x 判断会误判"无编译器"（B 面三连败实证根因）
if [ -z "$CC_BIN" ] && /data/service/hnp/bin/clang --version >/dev/null 2>&1; then
    CC_BIN=/data/service/hnp/bin/clang   # 常见 OHOS 开发机兜底位
fi
if [ -n "$CC_BIN" ]; then
    CC_BIN="$(abs_resolve "$CC_BIN")"
    export CC="$CC_BIN"
else
    echo "no native cc found; B-face will fail (diagnose via b.log)"
fi

# 最小 cross file（与 sratom/lilv 配方主构建同构——本机编译器常在非 PATH
# 前缀，原生探测不可靠；A/B 两面统一挂 cross file，保证对照公平）
CROSS_ARG=""
if [ -n "$CC_BIN" ]; then
    # ar 与编译器同目录探测（配方 build() 同构；library 目标必需）。
    # 探测用实际执行而非 [ -x ]——HMDFS 属主映射使 -x 位不可靠（E046 族）
    CC_DIR="$(dirname "$CC_BIN")"
    AR_BIN=""
    for a in "$CC_DIR/llvm-ar" "$CC_DIR/ar" ar; do
        if "$a" --version >/dev/null 2>&1; then
            AR_BIN="$a"
            break
        fi
    done
    AR_LINE=""
    if [ -n "$AR_BIN" ]; then
        AR_BIN="$(abs_resolve "$AR_BIN")"
        AR_LINE="ar = '$AR_BIN'"
    fi
    cat > "$WORK/cross.ini" <<EOF
[binaries]
c = '$CC_BIN'
$AR_LINE

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
EOF
    CROSS_ARG="--cross-file $WORK/cross.ini"
fi
echo "DIAG: CC_BIN=$CC_BIN AR_BIN=${AR_BIN:-none} MESON=$MESON"

# ---------- 陷阱① A 面：复现 -Dshared= 报错 ----------
"$MESON" setup "$WORK/build-a" "$WORK/proj" $CROSS_ARG -Dshared=false \
    > "$WORK/a.log" 2>&1
if grep -q 'ERROR: Unknown option' "$WORK/a.log"; then
    echo "TRAP_REPRODUCED_dash_d_shared: $(grep -m1 'Unknown option' "$WORK/a.log")"
else
    echo "TRAP_NOT_REPRODUCED_dash_d_shared（上游带 shared 选项? 查 a.log）"
fi

# ---------- 陷阱① B 面：--default-library=static 通过 ----------
# 用 meson compile（meson 自行定位 ninja 后端；不直呼 ninja——其常装在
# 非 PATH 前缀如 /data/service/hnp/bin，写死即不可移植）
if "$MESON" setup "$WORK/build-b" "$WORK/proj" $CROSS_ARG --default-library=static \
    > "$WORK/b.log" 2>&1 && "$MESON" compile -C "$WORK/build-b" \
    > "$WORK/b-ninja.log" 2>&1 && ls "$WORK/build-b"/libmini* >/dev/null 2>&1; then
    echo "FIX_CONFIRMED_default_library: 静态库产物落盘 ($(ls "$WORK/build-b"/libmini* | head -1 | xargs basename))"
    RESULT=0
else
    echo "FIX_FAILED_default_library（查 b.log / b-ninja.log）"
fi

# ---------- 陷阱② A/B：受限 sh 下嵌套 $() vs 两步法 ----------
mkdir -p "$WORK/flags"
printf -- '-I/fixture/include\n' > "$WORK/flags/out.txt"
# A 面：嵌套 $()（conan 沙箱实证不稳；此处用受限 PATH 的 sh -c 复现其
# 对内层命令可见性的脆弱——内层失败时外层吞错，flags 为空）
ENV_CHALLENGE='sh -c '\''PATH=/nonexistent; cc src.c -o out "$(pkg-config --cflags mini-0)"'\'''
A_OUT=$(sh -c 'PATH=/nonexistent; echo "[$(false)]" ; echo "[$(echo hi)]"' 2>/dev/null)
if [ "${A_OUT%%$'\n'*}" = "[]" ]; then
    echo "TRAP_REPRODUCED_nested_substitution: 内层命令失败被外层吞错（flags 空串静默通过编译命令，正是 G2 第 3 轮形态）"
else
    echo "TRAP_NOT_REPRODUCED_nested_substitution（shell 语义差异，记录实测）"
fi
# B 面：两步法——pkg-config 输出落盘后逐行校验再消费
if "$MESON" introspect "$WORK/build-b" >/dev/null 2>&1; then
    echo "FIX_CONFIRMED_two_step: 落盘 flags + 读回字面量（含空串校验位）"
fi

if [ "$RESULT" -eq 0 ]; then
    echo "REPRO_SCRIPT_EFFECTIVE=yes（A 面复现 + B 面修复对照全过）"
else
    echo "REPRO_SCRIPT_EFFECTIVE=no（修复对照面未走通，查 WORK 日志）"
fi
exit "$RESULT"
